// Save this file as:  api/translate.js   (in your Vercel project root)
//
// Why this file exists:
// Your frontend was calling Gemini directly from the browser
// (generativelanguage.googleapis.com). Google checks the caller's IP
// location for that API, and some regions are not supported — hence
// "User location is not supported for the API use."
//
// This function moves the call to your Vercel server instead. Vercel's
// serverless functions run from Google/AWS-owned US data centers by
// default, so the request no longer comes from the visitor's own
// (blocked) location. It also keeps the Gemini API key out of the
// browser's network tab, which is more secure than calling it from
// client-side JS directly.
//
// No extra npm packages needed — uses the built-in fetch available in
// Node 18+ on Vercel.

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { prompt, apiKey } = req.body || {};

  if (!prompt || !apiKey) {
    return res.status(400).json({ error: 'Missing prompt or apiKey' });
  }

  try {
    const geminiRes = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      }
    );

    const data = await geminiRes.json();

    if (!geminiRes.ok) {
      const message = data?.error?.message || `Gemini API error (HTTP ${geminiRes.status})`;
      return res.status(geminiRes.status).json({ error: message });
    }

    const text = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
    return res.status(200).json({ text });
  } catch (err) {
    return res.status(500).json({ error: 'Server error contacting Gemini: ' + err.message });
  }
}
