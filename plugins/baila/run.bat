@ECHO off
cd ..
call build.bat baila
call debug.bat > baila\test.txt
cd baila
