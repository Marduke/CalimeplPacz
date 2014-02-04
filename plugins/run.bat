@ECHO off
call build.bat %1
call debug.bat > %1\test.txt