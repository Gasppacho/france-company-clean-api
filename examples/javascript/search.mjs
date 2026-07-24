const query = process.argv[2] ?? "Qonto";
const baseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const url = new URL("/v1/companies/search", baseUrl);
url.searchParams.set("q", query);

const headers = {};
if (process.env.RAPIDAPI_KEY && process.env.RAPIDAPI_HOST) {
  headers["X-RapidAPI-Key"] = process.env.RAPIDAPI_KEY;
  headers["X-RapidAPI-Host"] = process.env.RAPIDAPI_HOST;
}

const response = await fetch(url, { headers });
const payload = await response.json();
if (!response.ok) {
  console.error(JSON.stringify(payload, null, 2));
  process.exit(1);
}
console.log(JSON.stringify(payload, null, 2));
