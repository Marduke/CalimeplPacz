cd ..\tmp
del /Q %USERPROFILE%\AppData\Roaming\calibre\plugins\*.*
"E:\data\calibre devel\Calibre Portable\Calibre\calibre-customize.exe" -b %CD%
"E:\data\calibre devel\Calibre Portable\Calibre\calibre-debug.exe" -e __init__.py
cd ..\plugins