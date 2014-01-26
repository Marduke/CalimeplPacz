@ECHO off
cd ..
call build.bat onlineknihovna
call debug.bat > onlineknihovna\test.txt
cd onlineknihovna
