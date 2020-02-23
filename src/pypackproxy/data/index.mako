<%inherit file='base.mako'/>

<%block name="title">Start</%block>

% if admin_enabled:
  <%block name="links"><a href="/admin/">Administration</a></%block>
% endif

<h2>Locally stored projects: ${len(projects)}</h2>

<ul>
% for project in projects:
  % if project_base_url:
    <li><a href="${project_base_url}${project}">${project}</a></li>
  % else:
    <li>${project}</li>
  % endif
% endfor
</ul>
