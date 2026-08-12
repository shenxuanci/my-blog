/* global hexo */

'use strict';

// 覆盖 Fluid 的评论注入点，让 Twikoo 的 path 由每篇文章的 front-matter 决定。
//
// 背景：Fluid 自带模板把 path 写成 `path: '<%= theme.twikoo.path %>'`（带引号且转义），
// 因此 _config.fluid.yml 里配置的 `window.location.pathname` 会被当作字面量字符串输出，
// 所有文章的评论都会落进同一个桶。这里改为：
//   - 旧文章用 front-matter 的 twikooPath（迁移前的 article_id），保住历史评论；
//   - 新文章没有该字段，回落到真实的页面路径。
//
// Fluid 的默认注入以优先级 -99 注册，注入项按 `inject/<point>/<name>` 去重，
// 所以这里用同名 default 在默认优先级注册即可覆盖，无需改动主题源码。

const TWIKOO_VIEW = `<% if ((!is_post() && !is_page()) || (is_post() && theme.post.comments.enable && page.comments) || (is_page() && page.comments)) { %>
  <article id="comments">
    <div id="twikoo"></div>
    <script type="text/javascript">
      Fluid.utils.loadComments('#comments', function() {
        Fluid.utils.createScript('<%= url_join(theme.static_prefix.twikoo, 'twikoo.all.min.js') %>', function() {
          twikoo.init({
            envId: '<%= theme.twikoo.envId %>',
            <% if (theme.twikoo.region) { %>region: '<%= theme.twikoo.region %>',<% } %>
            el: '#twikoo',
            path: JSON.parse(decodeURIComponent("<%- encodeURIComponent(JSON.stringify(String(page.twikooPath || url_for(page.path)))) %>")),
            lang: '<%= theme.twikoo.lang || "zh-CN" %>',
            onCommentLoaded: function() {
              Fluid.utils.listenDOMLoaded(function() {
                var imgSelector = '#twikoo .tk-content img:not(.tk-owo-emotion)';
                Fluid.plugins.imageCaption(imgSelector);
                Fluid.plugins.fancyBox(imgSelector);
              });
            }
          });
        });
      });
    </script>
    <noscript>Please enable JavaScript to view the comments</noscript>
  </article>
<% } %>`;

hexo.extend.filter.register('theme_inject', function(injects) {
  const themeConfig = hexo.theme.config;
  const twikoo = themeConfig.twikoo;

  if (!twikoo || !twikoo.envId) return;
  if (themeConfig.post.comments.type !== 'twikoo') return;

  if (themeConfig.post.comments.enable) {
    injects.postComments.raw('default', TWIKOO_VIEW);
  }
  injects.pageComments.raw('default', TWIKOO_VIEW);
});
