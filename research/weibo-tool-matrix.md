# 官方 CLI 与插件工具全量对照

此表由 `tools/sync-weibo-catalog.ps1` 生成；修改映射请编辑 `specs/weibo/browser-mapping.json`，再用 `-Offline` 重建。

官方目录版本：`457761d16c50510ec276524e9586d4c6193b82572e460d24da4cf3850aed9d03`。共 75 项，CLI 0.9.8。
快照时间及完整参数、枚举、说明见 [官方目录 JSON](../specs/weibo/official-cli-catalog.json)；[插件契约 JSON](../specs/weibo/tool-contract.json)保留所有拟用工具名及官方参数。

除 statuses update 已注册为仅草稿预演工具（enabled_preview_only）外，其余工具状态为 planned。下表的浏览器验证结果不等于正式插件已实现。partial 表示参数、权限、分页或返回语义不完全等价；unsupported 表示当前没有实现。GET/POST 为官方方法，不直接代表业务副作用。

已验证：read_passed=真实读取；single_read_passed=只验证单条；dry_run_passed=只验证预演；not_tested=尚未验证。

| 官方命令 / 用途 | 拟用模型工具名 | 方法 | 必填参数 | 浏览器对应 | 验证 | 差异与范围 |
| --- | --- | --- | --- | --- | --- | --- |
| `article collections/create` / 创建付费专栏 | `weibo_article_collections_create` | POST | title, money, content, video_nums, images, category_id | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `article collections/delete` / 删除专栏 | `weibo_article_collections_delete` | POST | id | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `article collections/info` / 查询专栏详情 | `weibo_article_collections_info` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `article collections/list` / 查询专栏列表 | `weibo_article_collections_list` | GET | page, limit, short_play | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `article collections/update` / 更新专栏 | `weibo_article_collections_update` | POST | id, title, money, images, content, video_nums, category_id | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `article config` / 查询发文配置 | `weibo_article_config` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `article preview` / 生成文章预览链接 | `weibo_article_preview` | GET | title, content, free_content, pay_type | partial: article.draftMarkdown | not_tested | 仅功能近似。后台草稿可能写入服务器，不等同只读官方预览；付费参数和免费预览范围尚未对齐。 |
| `article publish` / 发布文章 | `weibo_article_publish` | POST | title, content, text, pay_type | partial: article.publishMarkdown | not_tested | 仅工具存在；不能认定标题、短微博同步、pay_type 与付费/专栏语义兼容，不在首版开放。 |
| `attitudes create` / 发布一条表态 | `weibo_attitudes_create` | POST | id | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `attitudes destroy` / 删除一条表态 | `weibo_attitudes_destroy` | POST | id | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `attitudes show/biz` / 根据微博ID返回某条微博的赞列表 | `weibo_attitudes_show_biz` | GET | id | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments by_me/biz` / 获取当前登录用户发出的评论列表 | `weibo_comments_by_me_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments by_me/other` / 获取某个用户发出的评论列表 | `weibo_comments_by_me_other` | GET | uid | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments create` / 评论一条微博 | `weibo_comments_create` | POST | comment, id | partial: comment.create | not_tested | id 需转换为目标微博 URL，comment 映射 text；只确认工具存在，未测试预演或提交。 |
| `comments destroy` / 删除一条评论 | `weibo_comments_destroy` | POST | cid | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments mentions/biz` / 获取@当前登录用户的评论 | `weibo_comments_mentions_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments mentions/other` / 获取@某人的评论 | `weibo_comments_mentions_other` | GET | uid | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments reply` / 回复一条评论 | `weibo_comments_reply` | POST | cid, id, comment | unsupported: 无 | not_tested | comment.create 不能证明可以回复指定 cid；需单独实现评论楼层定位与结果核验。 |
| `comments show_batch/biz` / 批量获取评论内容 | `weibo_comments_show_batch_biz` | GET | cids | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments show/all` / 返回一条微博的全部评论列表 | `weibo_comments_show_all` | GET | id | partial: post.replies.list | read_passed | 指定微博评论读取已实测；字段、排序、过滤、分页与官方接口不保证一致，不能宣称完整等价。 |
| `comments show/biz` / 获取当前登录用户发布的微博下的评论列表 | `weibo_comments_show_biz` | GET | id | partial: post.replies.list | read_passed | 同一浏览器读取可作为实现参考；官方 biz 权限与返回契约未复现，正式工具尚未实现。 |
| `comments timeline/biz` / 获取当前登录用户发出及收到的评论列表 | `weibo_comments_timeline_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments timeline/other` / 获取某个用户发出和收到的评论列表 | `weibo_comments_timeline_other` | GET | uid | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments to_me/biz` / 获取当前登录用户收到的评论列表 | `weibo_comments_to_me_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `comments to_me/other` / 获取某个用户收到的评论列表 | `weibo_comments_to_me_other` | GET | uid | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/active_list` / 获取授权用户活跃或互动粉丝TOP20列表 | `weibo_friendships_followers_active_list` | GET | flag | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/age_group_count` / 获取某用户粉丝的年龄段、性别细分数据 | `weibo_friendships_followers_age_group_count` | GET | uid | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/biz` / 获取当前登录用户的粉丝列表 | `weibo_friendships_followers_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/demographics_day` / 获取用户粉丝的星座、兴趣标签和粉丝量级的细分数据 | `weibo_friendships_followers_demographics_day` | GET | uid, property | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/influence_top20` / 获取近7天转发或互动最多的粉丝TOP20（仅蓝V） | `weibo_friendships_followers_influence_top20` | GET | uid, time_span, flag | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/location_count` / 获取用户粉丝的地区细分数据 | `weibo_friendships_followers_location_count` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/online_time/biz` / 获取当前登录用户粉丝最近一周在线时段比例分布 | `weibo_friendships_followers_online_time_biz` | GET | type | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/source` / 获取某用户粉丝的关注来源 | `weibo_friendships_followers_source` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/trend_other/biz` / 获取当前登录用户的粉丝每天增加和减少数量 | `weibo_friendships_followers_trend_other_biz` | GET | starttime, endtime | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships followers/unfollower_count` / 获取最长近90天内每天取消关注该账户的用户数 | `weibo_friendships_followers_unfollower_count` | GET | uid, starttime, endtime | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `friendships friends/biz` / 获取当前登录用户的关注列表 | `weibo_friendships_friends_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `search hot_word_cate/biz` / 搜索分类榜单 | `weibo_search_hot_word_cate_biz` | GET | category | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `search hot_word/biz` / 微博热搜主榜 | `weibo_search_hot_word_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `search statuses/limited` / 搜索含某关键词的微博 | `weibo_search_statuses_limited` | GET | q, type | partial: search.weibo | not_tested | 搜索工具存在；q/type、结果范围、排序和分页尚未对齐，不能把普通网页搜索当成完整等价。 |
| `search suggestions/users/biz` / 搜用户搜索建议 | `weibo_search_suggestions_users_biz` | GET | q | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `short_url expand` / 将一个或多个短链接还原成原始的长链接 | `weibo_short_url_expand` | POST | url_short | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `short_url shorten` / 将一个或多个长链接转换成短链接 | `weibo_short_url_shorten` | POST | url_long | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses count_sp/biz` / 批量获取指定授权微博的转发数、评论数、赞数、阅读数 | `weibo_statuses_count_sp_biz` | GET | ids | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses count/biz` / 批量获取指定微博的转发数评论数喜欢数 | `weibo_statuses_count_biz` | GET | ids | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses destroy` / 删除微博信息 | `weibo_statuses_destroy` | POST | id | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses mentions/biz` / 获取@当前登录用户的微博列表 | `weibo_statuses_mentions_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses mentions/other` / 获取@某人的微博 | `weibo_statuses_mentions_other` | GET | uid | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses queryid/biz` / 通过微博（评论、私信）MID获取其ID | `weibo_statuses_queryid_biz` | GET | mid, type | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses querymid/biz` / 通过微博（评论、私信）ID获取其MID | `weibo_statuses_querymid_biz` | GET | id, type | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses repost` / 转发一条微博信息 | `weibo_statuses_repost` | POST | id, status | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses repost_timeline/all` / 返回一条微博的全部转发微博列表 | `weibo_statuses_repost_timeline_all` | GET | id | partial: post.repost.list | not_tested | 只确认转发列表工具存在，未测试；分页与覆盖范围需单独核对。 |
| `statuses repost_timeline/biz` / 获取当前登录用户发布的一条原创微博的最新转发微博 | `weibo_statuses_repost_timeline_biz` | GET | id | partial: post.repost.list | not_tested | 不保证复现官方 biz 的范围、筛选及分页语义。 |
| `statuses show_batch/biz` / 根据微博ID批量获取微博信息 | `weibo_statuses_show_batch_biz` | GET | ids | partial: post.get | single_read_passed | 只验证单条详情；批量 ids、失败项聚合及返回字段尚未实现。 |
| `statuses statistic/biz` / 返回近90天内发布的授权微博每天的被转发数、被评论数、被喜欢数、被点击数（区分短链、图片、视频点击） | `weibo_statuses_statistic_biz` | GET | id, starttime, endtime | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses update` / 发布一条微博信息 | `weibo_statuses_update` | POST | status | partial: post.create | dry_run_passed | v0.1.0 已注册 weibo_statuses_update，仅保存草稿和预演，不能真实发布。status 映射 text。visible、mblog_statement、地理位置等官方参数尚无浏览器等价实现，不得静默丢弃。 |
| `statuses upload` / 上传图片并发布一条微博 | `weibo_statuses_upload` | POST | pic, status | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses upload_pic` / 上传图片，返回图片id | `weibo_statuses_upload_pic` | POST | pic | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses upload_url_text` / 发布一条带单/多图的微博（需要组合上传图片接口） | `weibo_statuses_upload_url_text` | POST | pic_id, status | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `statuses user_timeline_batch` / 批量获取用户个人微博列表 | `weibo_statuses_user_timeline_batch` | GET | 无 | partial: user.posts.list | not_tested | 仅单用户候选工具；批量调度、部分失败处理和返回契约尚未实现。 |
| `statuses user_timeline/biz` / 获取当前登录用户发布的微博 | `weibo_statuses_user_timeline_biz` | GET | 无 | partial: user.posts.list | not_tested | 工具存在；当前账号身份解析、读取范围及官方参数对齐尚未实现。 |
| `statuses user_timeline/other` / 获取其他用户发布的微博 | `weibo_statuses_user_timeline_other` | GET | uid | partial: user.posts.list | not_tested | 工具存在；uid 对齐、分页和过滤条件尚未实测。 |
| `tags biz` / 获取当前登录用户的标签 | `weibo_tags_biz` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `tags tags_batch/other` / 批量获取用户标签 | `weibo_tags_tags_batch_other` | GET | uids | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `users behavior_trend` / 获取授权用户行为数据每日变化趋势 | `weibo_users_behavior_trend` | GET | starttime, endtime | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `users behavior_trend/biz` / 获取他人用户行为数据每日变化趋势 | `weibo_users_behavior_trend_biz` | GET | uid, starttime, endtime | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `users counts_batch/other` / 批量获取用户的粉丝数、关注数、微博数 | `weibo_users_counts_batch_other` | GET | uids | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `users receive_like_count` / 获取某用户近90天每天的被喜欢数 | `weibo_users_receive_like_count` | GET | starttime, endtime | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `users show_batch/other` / 批量获取其他用户的基本信息 | `weibo_users_show_batch_other` | GET | 无 | partial: user.get | not_tested | 候选为逐个读取；批量 ID/昵称转换、部分失败及官方返回字段未实现。 |
| `users show/biz` / 获取当前登录用户信息 | `weibo_users_show_biz` | GET | 无 | partial: user.get | not_tested | user.get 要求 URL 或昵称，不能用 auth.get 代替当前用户资料；账号身份解析和字段尚未实现。 |
| `users statistic/biz` / 获取当前登录用户近90天每天的被点击数（区分短链、图片点击）、被阅读数、用户去重的被阅读数 | `weibo_users_statistic_biz` | GET | starttime, endtime | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `wbindex ranking/showComing` / 综艺-待播榜 | `weibo_wbindex_ranking_showComing` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `wbindex ranking/showHot` / 综艺-热播榜 | `weibo_wbindex_ranking_showHot` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `wbindex ranking/tvComing` / 剧集-待播榜 | `weibo_wbindex_ranking_tvComing` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `wbindex ranking/tvHot` / 剧集-热播榜 | `weibo_wbindex_ranking_tvHot` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |
| `wbindex ranking/tvRole` / 剧集-热议角色榜 | `weibo_wbindex_ranking_tvRole` | GET | 无 | unsupported: 无 | not_tested | 当前浏览器适配器没有等价工具；正式插件尚未实现此操作。 |

## 浏览器补充能力

以下单独命名，避免冒充官方等价接口。

| 适配器工具 | 用途 | 验证 |
| --- | --- | --- |
| `auth.get` | 会话状态检测，须叠加独立登录判断 | guarded_read_passed |
| `page.get` | 页面诊断 | not_tested |
| `timeline.home.list` | 读取首页动态，当前官方目录没有直接同名对应项 | read_passed |
| `post.get` | 单条详情；用于官方批量读取的部分能力参考 | read_passed |
| `article.listDrafts` | 文章草稿列表，不在当前官方目录直接对应项中 | not_tested |
| `article.getDraft` | 读取文章草稿 | not_tested |
| `search.ai.summary` | 网页 AI 搜索摘要，不等于官方微博搜索接口 | not_tested |

契约、参数差异处理和开发顺序见 [正式插件设计](../docs/plugin-design.md)。诊断命令来源与复现见 [探测命令说明](weibo-probe.md)。
