importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyBcOZ_G6bmj1wjkc2f97tgTh9BMi3ws9ZA",
  authDomain: "appcartera123.firebaseapp.com",
  projectId: "appcartera123",
  storageBucket: "appcartera123.firebasestorage.app",
  messagingSenderId: "206685291968",
  appId: "1:206685291968:web:6f2db50f8a7ed0e107f425"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification;
  self.registration.showNotification(title, { body, icon: '/icon.png' });
});
