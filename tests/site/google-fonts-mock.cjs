// Offline stand-in for Google Fonts, loaded by Next's NEXT_FONT_GOOGLE_MOCKED_RESPONSES
// test hook (an absolute path to this file). Every stylesheet request gets a font address
// with no extension, the Google response that crashed site builds (#319). The site's
// fonts ship with it, so a build that asks Google for any font fails here.
module.exports = new Proxy({}, {
  get(_, url) {
    if (typeof url !== "string" || !url.startsWith("https://fonts.googleapis.com/")) return undefined;
    return `/* latin */
@font-face {
  font-family: 'Mock';
  font-style: normal;
  font-weight: 400;
  src: url(https://fonts.gstatic.com/l/font?kit=mock) format('woff2');
}`;
  },
});
