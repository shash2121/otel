import http from "k6/http";
export const options = {
  scenarios: { burst: {
    executor: "ramping-arrival-rate", startRate: 0, timeUnit: "1s",
    preAllocatedVUs: 20, maxVUs: 200,
    stages: [
      { target: 0, duration: "10s" },
      { target: 250, duration: "5s" },
      { target: 250, duration: "30s" },  // hold long enough for alert
      { target: 0, duration: "20s" },
      { target: 250, duration: "5s" },
      { target: 250, duration: "30s" },
      { target: 0, duration: "10s" },
    ],
  }},
  thresholds: { http_req_duration: ["p(95)<2000", "p(99)<5000"], http_req_failed: ["rate<0.15"] },
};
export default function () {
  http.get(`${__ENV.BASE_URL}/products`);
  http.get(`${__ENV.BASE_URL}/products/search?q=mouse`);
  // 50% chance of order — serious INSERT pressure
  if (Math.random() < 0.5) {
    http.post(`${__ENV.BASE_URL}/orders`, JSON.stringify({ product_id: Math.floor(Math.random() * 8) + 1, quantity: 1 }),
      { headers: { "Content-Type": "application/json" } });
  }
}
