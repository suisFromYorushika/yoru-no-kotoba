-- 夜の言葉：GitHub Pages 版的云端进度（Supabase）
-- 用法：Supabase 控制台 → SQL Editor → 粘贴整个文件 → Run。重复运行也没关系。
--
-- 每个账号一行，data 里是网页的进度 JSON：
--   {"v": 2, "learned": [词…], "srs": [[词, 盒子, 到期日]…], "log": [[日, 复习, 新掌握, 新词, 测验]…]}
-- 行级安全（RLS）保证每个人只能读写自己那一行；网页里用的 publishable key 本来就是公开的，靠 RLS 保护数据。

create table if not exists public.progress (
  user_id    uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  data       jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.progress enable row level security;

drop policy if exists "读自己的进度" on public.progress;
create policy "读自己的进度" on public.progress
  for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "新建自己的进度" on public.progress;
create policy "新建自己的进度" on public.progress
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "更新自己的进度" on public.progress;
create policy "更新自己的进度" on public.progress
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- 只给登录用户读写权限；未登录的访客什么都访问不到
revoke all on public.progress from anon;
grant select, insert, update on public.progress to authenticated;
