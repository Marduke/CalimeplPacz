@ECHO off
cd ..
call build.bat pitaval
call debug.bat > pitaval\test.txt
cd pitaval
