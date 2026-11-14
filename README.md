# ndhmdSuite

Version: 4.35

Publisher: ndhmd

ndhmdSuite is a comprehensive toolset designed for efficient document authoring and compilation. The suite features the main dedicated editor (ndhmdwriter) alongside integrated auxiliary tools and compilation wrappers like ksruncltex.

* Homepage: https://xltxlvr.github.io/ndhmdsuite

## Included Components
ndhmdwriter: The primary graphical editor and interface for the suite.

ksruncltex: Bundled compilation wrapper, automatically configured during the installation process.

Resources: Core configuration and resource files, maintained in the user profile directory.

## Installation
Download the ndhmdSuite_Setup.exe installer.

Run the executable. The setup supports both All Users (requires Administrator privileges) and Current User installation modes.

If a previous version of ndhmdSuite is detected on your system, the installer will prompt you to automatically and cleanly remove it before proceeding.

Select your preferred language (English or Korean) and follow the setup wizard.

## Automated Setup Actions
During installation, the setup executable automatically performs the following system configurations:

Environment Variables: Appends the installation directory to your system or user PATH, allowing seamless command-line access to the suite's tools from any directory.

Resource Deployment: Copies necessary user resources directly to %USERPROFILE%\ndhmd4tex\.

Script Initialization: Silently executes the ksruncltex installation batch script to register necessary compilation elements.

Shortcuts: Generates Desktop and Start Menu shortcuts for ndhmdwriter.exe.

## Uninstallation
ndhmdSuite can be entirely removed via the Windows "Apps & features" or "Add or Remove Programs" settings.

The uninstaller is designed for a clean rollback. It will safely remove the application directory from your PATH environment variable and delete the installed binaries. (Note: User-generated files or specific configurations in the %USERPROFILE%\ndhmd4tex\ directory may need to be removed manually if no longer needed.)