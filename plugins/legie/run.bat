@ECHO off
cd ..
call build.bat legie
call debug.bat > legie\test.txt
cd legie
