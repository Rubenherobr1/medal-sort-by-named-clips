# Sort by Named Clips in [Medal](https://medal.tv/)

Do you usually give a memorable name to Medal clips that are amazing, and don't name the other
clips that you have? Have you ever wanted to see only the clips that you gave a name to?

This python script does exactly that: it only gets the clips that are named, and saves it to 
somewhere **(TBD)**, since Medal dosen't give that filter option, and the video files for the 
clips aren't renamed to what name you give them inside Medal. 

**Note**: This is NOT an official script from Medal.


## Known supported versions

This script was developed for the following versions:
- **Latest Stable:** 2629.329.1
- **Recorder version:** 2629.2224.1

To check your version, go to **Settings** and **scroll down**. It should be at the bottom.


## Issues that might happen

### Updating or downgrading Medal

The script may or may not work in future or past versions. If you think it does not work in your version,
feel free to open a PR or an issue so i can see what i can do!

### Changing devices

It is likely that if you change devices and simply copy-paste the generated folder onto your new device,
the script's "syncing" (deleting old clips and adding new ones) will 100% break, since it uses id's that
are local to your device to sync.

So, if you do, you should delete the old folder and execute the script again to generate a new one. 

### Manually imported clips' title

If you import a clip manually it will have the clip's filename as it's title, just how it appears on Medal
iself. So, all i can do for that case is ignore clips with a certain format in their filenames that are
automaticly generated in the same way (like how gamebar clips always have the "window_name date time" format).

If you want me to add support for a specific format open an issue!


## Special thanks

Special thanks to **@HeartzzSamm** for sharing their database so i could use an actual dataset from someone that uses Medal
often. It allowed me to fix lots of bugs that i wouldn't even be able to known they would happen.

Also, this project was done for -user-'s use case, so thanks for giving this idea aswell!


# Deleting the generated JSON file WILL break things


