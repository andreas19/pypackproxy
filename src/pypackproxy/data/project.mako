<%inherit file='admin.mako'/>

<%block name="links">${parent.links()} - <a href="/admin">Overview</a></%block>

% if files is None:
  <% return STOP_RENDERING %>
% endif

<h3>Project: ${project}</h3>

<form method="post">
  <button id="delproj" name="delproj" value="${project}">Delete project</button>
</form>
<script>
  document.getElementById("delproj").addEventListener("click", function(e) {
    if (!confirm('Delete project "${project}" and all files?')) {
      e.preventDefault()
    }
  })
</script>

<h4>Files</h4>
<form method="post" enctype="multipart/form-data">
  <button>Upload</button> files
  <input type="file" name="upfiles" multiple required>
</form><br>

% if not files:
  <% return STOP_RENDERING %>
% endif

<form method="post" id="delfilesform">
  <button id="delfiles">Delete files</button>
  <table class="files">
  % for file in files:
    <tr>
      <td><input type="checkbox" name="delfiles" value="${file.name}"></td>
      <td><a href="${file.url}">${file.name}</a></td>
      <td>${file.size}B</td>
      <td>${file.mtime}</td>
    </tr>
  % endfor
  </table>
</form>
<script>
  document.getElementById("delfiles").addEventListener("click", function(e) {
    var elems = document.forms.delfilesform.elements
    var cnt = 0
    for (let i = 0; i < elems.length; i++) {
        if (elems[i].type == 'checkbox' && elems[i].checked) {
            cnt += 1
        }
    }
    if (cnt == 0 || !confirm('Delete files?')) {
        e.preventDefault()
    }
  })
</script>
