import http from "k6/http";
export const options = {
  scenarios: { browsing: {
    executor: "constant-arrival-rate", rate: 3, timeUnit: "1s",
    duration: "2m", preAllocatedVUs: 5, maxVUs: 10,
  }},
};
export default function () {
  http.get(`${__ENV.BASE_URL}/products`);
  http.get(`${__ENV.BASE_URL}/products/search?q=mouse`);
}
