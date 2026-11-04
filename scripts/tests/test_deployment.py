import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy_ecs
import release_academy
import publish_frontend


class DeploymentTests(unittest.TestCase):
    def test_final_release_allows_only_existing_dependent_alarm(self):
        alarm = {'Action': 'Modify', 'ResourceType': 'AWS::CloudWatch::Alarm', 'LogicalResourceId': 'ApiMemoryAlarm', 'Replacement': 'False'}
        self.assertTrue(release_academy.safe_final_change(alarm))
        for changes in [{'Action': 'Remove'}, {'Replacement': 'True'}, {'LogicalResourceId': 'OtherAlarm'}, {'Action': 'Add'}]:
            self.assertFalse(release_academy.safe_final_change({**alarm, **changes}))

    def session(self, account=deploy_ecs.ACCOUNT):
        clients = {name: Mock() for name in ["sts", "cloudformation", "ecs", "ecr", "s3"]}
        clients["sts"].get_caller_identity.return_value = {"Account": account}
        session = Mock()
        session.client.side_effect = clients.__getitem__
        return session, clients

    def test_api_plan_pins_previous_resolved_ami_instead_of_moving_ssm_key(self):
        session, clients = self.session()
        cfn = clients['cloudformation']
        cfn.describe_stacks.return_value = {'Stacks': [{'Parameters': [
            {'ParameterKey': 'EcsAmi', 'ParameterValue': '/aws/service/ecs/recommended/image_id', 'ResolvedValue': 'ami-0123456789abcdef0'}]}]}
        cfn.describe_change_set.return_value = {'Changes': []}
        with patch.object(deploy_ecs.boto3, 'Session', return_value=session), \
             patch.object(deploy_ecs, 'save'), patch('builtins.print'), \
             patch.object(sys, 'argv', ['deploy_ecs.py', 'plan', '--component', 'compute', '--change-set', 'pin-ami', '--image', 'fictional@sha256:' + 'a' * 64]):
            deploy_ecs.main()
        parameters = {p['ParameterKey']: p for p in cfn.create_change_set.call_args.kwargs['Parameters']}
        self.assertEqual(parameters['EcsAmi'], {'ParameterKey': 'EcsAmi', 'ParameterValue': 'ami-0123456789abcdef0'})

    def test_wrong_account_never_reaches_cloudformation(self):
        session, clients = self.session("000000000000")
        with patch.object(release_academy.boto3, "Session", return_value=session), \
             patch.object(sys, "argv", ["release_academy.py", "snapshot"]), self.assertRaises(RuntimeError):
            release_academy.main()
        clients["cloudformation"].describe_stacks.assert_not_called()
        self.assertEqual(session.client.call_args_list[0].args, ("sts",))
        self.assertEqual(session.client.call_count, 1)

    def test_migration_failure_prevents_api_release(self):
        session, clients = self.session()
        clients["cloudformation"].describe_stacks.return_value = {"Stacks": [{"Outputs": [{"OutputKey": "ApiTaskDefinitionArn", "OutputValue": "old:1"}]}]}
        clients["ecs"].describe_task_definition.return_value = {"taskDefinition": {"taskDefinitionArn": "old:1"}}
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "release.json").write_text(json.dumps({"previous_task_definition": "old:1", "stage_change_set": "stage"}))
            def invoke(*args):
                if args[0] == "migrate":
                    raise subprocess.CalledProcessError(1, "migration")
            with patch.object(release_academy, "RESULTS", Path(folder)), \
                 patch.object(release_academy.boto3, "Session", return_value=session), \
                 patch.object(sys, "argv", ["release_academy.py", "deploy"]), \
                 patch.object(release_academy, "command", side_effect=invoke) as command, \
                 self.assertRaises(subprocess.CalledProcessError):
                release_academy.main()
            self.assertEqual([call.args[0] for call in command.call_args_list], ["apply", "migrate"])

    def test_data_replacement_is_refused_before_execution(self):
        session, clients = self.session()
        cfn = clients["cloudformation"]
        cfn.describe_change_set.return_value = {"Status": "CREATE_COMPLETE", "ExecutionStatus": "AVAILABLE", "Changes": [{"ResourceChange": {
            "Action": "Modify", "Replacement": "True", "ResourceType": "AWS::RDS::DBInstance"}}]}
        with patch.object(deploy_ecs.boto3, "Session", return_value=session), \
             patch.object(sys, "argv", ["deploy_ecs.py", "apply", "--component", "compute", "--change-set", "review"]), \
             self.assertRaisesRegex(RuntimeError, "deletion/replacement"):
            deploy_ecs.main()
        cfn.execute_change_set.assert_not_called()

    def test_existing_frontend_release_cannot_be_overwritten_with_different_content(self):
        session, clients = self.session()
        clients["s3"].head_object.return_value = {"Metadata": {"sha256": "another-release"}}
        with tempfile.TemporaryDirectory() as folder:
            frontend = Path(folder) / "frontend"
            frontend.mkdir()
            (frontend / "index.html").write_text("<!doctype html><title>Fictitious</title>")
            with patch.object(publish_frontend, "ROOT", Path(folder)), \
                 patch.object(publish_frontend.boto3, "Session", return_value=session), \
                 patch.object(publish_frontend, "outputs", return_value={"WebBucketName": "fictional-private-web"}), \
                 patch.object(sys, "argv", ["publish_frontend.py", "--release", "existing"]), \
                 self.assertRaisesRegex(RuntimeError, "different content"):
                publish_frontend.main()
        clients["s3"].put_object.assert_not_called()
