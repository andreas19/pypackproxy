<!DOCTYPE html>
<html>
  <head>
    <title>${progname} ${progversion} - <%block name="title"/></title>
    <style>
      body { font-family: sans-serif; }
      div.message { border:solid 1px; padding:2px; margin:0px 50px 20px 0px }
      div.message.error { color: red; }
      div.message.success { color: green; }
      table.files { border: 1px solid; border-collapse:collapse; margin-top:5px }
      table.files td { border:1px solid; padding:0px 2px }
    </style>
  </head>
  <body>
    <h1>${progname}</h1>

    <%block name="links"/>

    ${next.body()}
  </body>
</html>
