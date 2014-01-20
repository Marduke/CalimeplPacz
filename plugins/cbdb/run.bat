@ECHO off
cd ..
call build.bat cbdb
call debug.bat > cbdb\test.txt
cd cbdb