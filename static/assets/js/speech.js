function tts(text) {
    if ('speechSynthesis' in window) {
        // speechSynthesis.getVoices().forEach(function(voice) {
        //     console.log(voice.name, voice.default ? voice.default :'');
        // });  
        var msg = new SpeechSynthesisUtterance();
        var voices = window.speechSynthesis.getVoices();        
        let obj;
        for (var i=0; i < voices.length; i++) {
            if (voices[i].name === "English (America)") {
                console.log(voices[i])
                obj = voices[i]
                msg.voice = voices[i];
            }
        }
        msg.voiceURI = obj.voiceURI; 
        msg.volume = 1; // From 0 to 1
        msg.rate = 0.75; // From 0.1 to 10
        msg.pitch = 2; // From 0 to 2
        msg.text = text;
        msg.lang = obj.lang;
        console.log(msg);
        speechSynthesis.speak(msg);
    }
    else{
        alert("Sorry, your browser doesn't Voice Support!");
    }
}