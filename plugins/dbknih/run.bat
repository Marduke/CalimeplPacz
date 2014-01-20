@ECHO off
cd ..
call build.bat dbknih
call debug.bat > dbknih\test.txt
cd dbknih