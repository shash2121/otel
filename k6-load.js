import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    constant_load: {
      executor: "ramping-arrival-rate",
      startRate: 1,
      timeUnit: "1s",
      preAllocatedVUs: 10,
      maxVUs: 50,
      stages: [
        { target: 5, duration: "30s" },
        { target: 10, duration: "1m" },
        { target: 20, duration: "1m" },
        { target: 5, duration: "30s" },
      ],
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    http_req_failed: ["rate<0.01"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:5001";

export default function () {
  const routes = [
    { method: "GET", path: "/" },
    { method: "GET", path: "/health" },
    { method: "GET", path: "/chuck" },
  ];

  for (const r of routes) {
    const res = http.request(r.method, `${BASE}${r.path}`);
    check(res, { "status 200": (r) => r.status === 200 });
  }

  // Product listing — hits both services, creates distributed trace
  const productsRes = http.get(`${BASE}/products`);
  check(productsRes, { "products ok": (r) => r.status === 200 && r.json("count") > 0 });

  // Create an order ~30% of the time — POST request, different code path
  if (Math.random() < 0.3) {
    const orderRes = http.post(
      `${BASE}/orders`,
      JSON.stringify({ product_id: Math.floor(Math.random() * 8) + 1, quantity: 1 }),
      { headers: { "Content-Type": "application/json" } }
    );
    check(orderRes, { "order created": (r) => r.status === 201 });
  }

  sleep(Math.random() * 2 + 0.5);
}
