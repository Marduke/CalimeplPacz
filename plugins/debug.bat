cd ..\tmp
%CALIBRE_PATH%calibre-customize -b %CD%
%CALIBRE_PATH%calibre-debug -e __init__.py
cd ..\plugins