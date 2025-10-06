import React, { useState } from 'react';

function SocialPostCreator() {
  const [language, setLanguage] = useState('en');
  const [parts, setParts] = useState({
    caption: true,
    hook: true,
    cta: true,
    hashtags: true,
  });
  const [useEmojis, setUseEmojis] = useState(true);

  const handleChange = (e) => {
    setParts({ ...parts, [e.target.name]: e.target.checked });
  };

  const handleGenerate = () => {
    // Εδώ θα βάλεις τη λογική παραγωγής περιεχομένου (AI, κλπ)
    alert('Generated post!');
  };

  return (
    <div>
      <h2>Δημιουργία Δημοσίευσης για Social Media</h2>
      <label>
        Επιλογή Γλώσσας:
        <select value={language} onChange={e => setLanguage(e.target.value)}>
          <option value="en">Αγγλικά</option>
          <option value="el">Ελληνικά</option>
        </select>
      </label>
      <div>
        <label>
          <input type="checkbox" name="caption" checked={parts.caption} onChange={handleChange} />
          Caption
        </label>
        <label>
          <input type="checkbox" name="hook" checked={parts.hook} onChange={handleChange} />
          Hook
        </label>
        <label>
          <input type="checkbox" name="cta" checked={parts.cta} onChange={handleChange} />
          CTA
        </label>
        <label>
          <input type="checkbox" name="hashtags" checked={parts.hashtags} onChange={handleChange} />
          Hashtags
        </label>
      </div>
      <label>
        <input type="checkbox" checked={useEmojis} onChange={e => setUseEmojis(e.target.checked)} />
        Προσθήκη Emojis
      </label>
      <button onClick={handleGenerate}>Δημιούργησε</button>
    </div>
  );
}

export default SocialPostCreator;
