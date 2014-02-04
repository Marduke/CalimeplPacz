@ECHO off
cd ..
@call build.bat dbknih
@call debug.bat > dbknih\test.txt
call test.bat > dbknih\result.txt
cd dbknih