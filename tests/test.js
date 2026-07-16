import http from "k6/http";
import { check } from "k6";

export const options = {
  gracefulStop: "0s",
  noConnectionReuse: false,
  noVUConnectionReuse: false,
};

export default function () {
  const res = http.get("http://127.0.0.1:8000/", {
    headers: {
      Connection: "keep-alive",
    },
  });

  check(res, {
    "status is 200": (r) => r.status === 200,
  });
}