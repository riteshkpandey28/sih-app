function tts(text) {
  var u = new SpeechSynthesisUtterance();
  u.text = text;
  speechSynthesis.speak(u);
}
