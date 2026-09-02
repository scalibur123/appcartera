const admin = require('firebase-admin');

if (!admin.apps.length) {
  const credential = process.env.FIREBASE_CREDENTIALS
    ? admin.credential.cert(JSON.parse(process.env.FIREBASE_CREDENTIALS))
    : admin.credential.cert(require('./firebase-credentials.json'));
  admin.initializeApp({ credential });
}

async function sendNotification(token, title, body, tckr) {
  try {
    // Payload SOLO data: sin bloque "notification" el navegador no pinta
    // ninguna notificacion por su cuenta. La unica que se muestra es la que
    // dibuja firebase-messaging-sw.js en onBackgroundMessage.
    await admin.messaging().send({
      token,
      data: tckr ? { title, body, tckr: String(tckr) } : { title, body },
      webpush: {
        headers: { Urgency: 'high', TTL: '3600' }
      }
    });
    console.log(`✅ Notificación enviada: ${title}`);
  } catch (err) {
    console.error('❌ Error notificación:', err.message);
  }
}

module.exports = { sendNotification };
