<%inherit file='base.mako'/>

<%block name="title">Administration</%block>

<%block name="links">
  <a href="/">Startpage</a>
  % if logged_in:
    - <a href="?logout=1">Logout</a>
  % endif
</%block>

<h2>Administration</h2>

% if message:
  <div class="message ${'error' if message[1] else 'success'}">${message[0]}</div>
% endif

${next.body()}
