# cool-webports-games
this is basically some of the webports that i am working on for diffrent games and to learn more about diffrent game engines

expect for fnaf games (as im in love with fnaf since i was like 5yo?) and other small indie games that could be cool as a webport playing on the go :)

soon i will make webapps for every webport i will make and introduce it here to play ONLY FOR ARCHIVAL PURPOSES OFC. NO ASSETS WILL BE UPLOADED FOR COPYRIGHT REASONS, AND I WILL NOT TELL YOU HOW TO USE MY TOOLS TO EXTRACT THEM!

fnaf1: https://fnaf1.motan-femboy.cc/ --its in a rough shape still optimizing and fixing bugs ,and yes i am aware of the fact that if you modify the value in the local storage of your broswer you can skip nights, its intentional lol, you are cheating yourself on a offline game , great job lol! code below to stop shitting yourself when you want to tell me that you modifed a single public value to 5 to skip to night 5 :)), either way the code is public in the repo lol
```javascript
const storageKey = 'fnaf1-archive-save-v1';
let saveData = {};
try { saveData = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch (_) {}
``` 
