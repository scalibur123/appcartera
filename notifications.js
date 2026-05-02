const admin = require('firebase-admin');
const serviceAccount = require('./firebase-credentials.json');

if (!admin.apps.length) {
  admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
  });
}

async function sendNotification(token, title, body) {
  try {
    await admin.messaging().send({ token, notification: { title, body } });
    console.log(`✅ Notificación enviada: ${title}`);
  } catch (err) {
    console.error('❌ Error notificación:', err.message);
  }
}

module.exports = { sendNotification };
