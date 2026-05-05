const admin = require('firebase-admin');

if (!admin.apps.length) {
  const credential = process.env.FIREBASE_CREDENTIALS
    ? admin.credential.cert(JSON.parse(process.env.FIREBASE_CREDENTIALS))
    : admin.credential.cert(require('./firebase-credentials.json'));
  admin.initializeApp({ credential });
}

async function sendNotification(token, title, body) {
  try {
    await admin.messaging().send({ token, notification: { title, body }, apns: { headers: { 'apns-collapse-id': title } }, android: { collapseKey: title } });
    console.log(`✅ Notificación enviada: ${title}`);
  } catch (err) {
    console.error('❌ Error notificación:', err.message);
  }
}

module.exports = { sendNotification };
