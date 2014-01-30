@ECHO off
cd ..
call build.bat kdb
call debug.bat > kdb\test.txt
cd kdb
