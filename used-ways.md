использованные способы, которые не сработали (только дополнять):

- **Tor + FlareSolverr + undetected-chromedriver** (USE_TOR_PARSER=true, по умолчанию)
  - Метод 1: curl_cffi (быстрый, без браузера)
  - Метод 2: undetected-chromedriver (браузер через Tor)
  - Метод 3: FlareSolverr (обход Cloudflare)
- nodriver (USE_TOR_PARSER=false, резерв)

рекомендуемый способ для попытки:

- **Camoufox** (USE_CAMOUFOX_PARSER=true) — Firefox-based anti-detect, Playwright API