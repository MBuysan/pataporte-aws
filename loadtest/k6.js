// Load test against the public read endpoints only (no accounts, no writes).
//   k6 run -e BASE_URL=http://localhost:8000 -e PROFILE=smoke loadtest/k6.js
// PROFILE=scale ramps to VUS (default 40) and holds for HOLD (default 7m): ~10 min in total,
// enough for the ALBRequestCountPerTarget / CPU target-tracking policies to add api tasks.
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
const VUS = Number(__ENV.VUS || 40);
const HOLD = __ENV.HOLD || '7m';

const profiles = {
  smoke: [
    { duration: '10s', target: 5 },
    { duration: '20s', target: 5 },
  ],
  scale: [
    { duration: '2m', target: VUS },
    { duration: HOLD, target: VUS },
    { duration: '1m', target: 0 },
  ],
};

const PROFILE = __ENV.PROFILE || 'smoke';
if (!profiles[PROFILE]) throw new Error(`unknown PROFILE '${PROFILE}' (smoke|scale)`);

export const options = {
  stages: profiles[PROFILE],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
    checks: ['rate>0.99'],
  },
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const health = http.get(`${BASE_URL}/api/health`, { tags: { name: 'health' } });
  check(health, { 'health 200': (r) => r.status === 200 });

  const tipos = http.get(`${BASE_URL}/api/vacunas/tipos`, { tags: { name: 'vacunas_tipos' } });
  check(tipos, { 'tipos 200': (r) => r.status === 200 });

  sleep(0.5);
}
