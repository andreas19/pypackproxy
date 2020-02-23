<%inherit file='admin.mako'/>

<form method="post">
  New project directory
  <input type="text" name="newdir" autofocus required>
  <button>Create</button>
</form>
<br>

<h3>Locally stored projects: ${len(projects)}</h3>

<ul>
% for project in projects:
  % if project_base_url:
    <li><a href="${project_base_url}${project}">${project}</a></li>
  % else:
    <li>${project}</li>
  % endif
% endfor
</ul>
