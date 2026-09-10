@echo off
REM Compiles the CUDA swarm searcher. Run from the problems/erdos/64 directory or from here.
REM Locates the MSVC environment first, because nvcc needs cl.exe on PATH.

setlocal

set SCRIPT_DIR=%~dp0
set SRC=%SCRIPT_DIR%swarm_857.cu
set OUT=%SCRIPT_DIR%swarm_857.exe

REM sm_89 is Ada Lovelace (RTX 40 series). Override with: set CUDA_ARCH=sm_86
if not defined CUDA_ARCH set CUDA_ARCH=sm_89

if defined VCINSTALLDIR goto :compile

set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if exist "%VCVARS%" goto :havevars
set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if exist "%VCVARS%" goto :havevars
set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if exist "%VCVARS%" goto :havevars
set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"
if exist "%VCVARS%" goto :havevars
set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat"
if exist "%VCVARS%" goto :havevars

echo ERROR: could not find vcvars64.bat. Install the MSVC build tools, or run this
echo        script from a Developer Command Prompt so VCINSTALLDIR is already set.
exit /b 1

:havevars
call "%VCVARS%" >nul

:compile
nvcc -O3 -std=c++17 -arch=%CUDA_ARCH% "%SRC%" -o "%OUT%"
if errorlevel 1 (
  echo ERROR: nvcc failed.
  exit /b 1
)

echo Built %OUT% for %CUDA_ARCH%.
endlocal
