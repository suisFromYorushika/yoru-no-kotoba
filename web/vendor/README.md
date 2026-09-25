# 第三方文件

| 文件 | 来源 | 许可证 |
|---|---|---|
| `supabase-js-2.117.2.js` | [@supabase/supabase-js](https://github.com/supabase/supabase-js) 2.117.2 的浏览器版（`dist/umd/supabase.js`，来自 jsDelivr） | MIT |

放在仓库里而不是从 CDN 加载，是为了在 CDN 访问不稳定的网络环境下也能登录。只有在 `data/site.json` 里配置了 Supabase 时，网页才会加载它。
