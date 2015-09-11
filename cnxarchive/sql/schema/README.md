# Archive Schema

Here lies database schema files.
When these files are put together they comprise the entire archive schema.
The order of these files is defined via ``manifest.json``
in this and any subdirectory.

### manifest.json files

Each directory should contain a ``manifest.json``
if it is to be included in the schema.

The contents of the file is an array of objects or strings.
The basic scheme looks like this:

    [
      "tables.sql",
      {
        "file": "strange-triggers.sql",
        "description": "Contains a strange trigger declaration"
      },
      {
        "file": "functions",
        "description": "Custom database functions in a functions directory"
      }
    ]

In this example the first item of the array is a simple filename.
The second and third items are objects with file and description data.
The description is not required, but it is perhaps helpful to other developers.
Also, the third item points to a directory rather than a file.

The order which the files appear in the array is how they will be included.

If a file in the directory is not mentioned in this array,
it will be ignored.

All file names are relative to the ``manifest.json`` file.
