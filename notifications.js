class NotificationManager {
  constructor() {
    this.storageKey = 'appcartera_notifications';
    this.pricesKey = 'appcartera_prev_prices';
    this.loadNotifications();
  }
  loadNotifications() {
    const stored = localStorage.getItem(this.storageKey);
    this.notifications = stored ? JSON.parse(stored) : [];
  }
  saveNotifications() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.notifications));
  }
  savePreviousPrices(pricesObject) {
    localStorage.setItem(this.pricesKey, JSON.stringify(pricesObject));
  }
  getPreviousPrices() {
    const stored = localStorage.getItem(this.pricesKey);
    return stored ? JSON.parse(stored) : {};
  }
  checkChanges(currentPrices, dataArray) {
    const prevPrices = this.getPreviousPrices();
    const newNotifications = [];
    for (const item of dataArray) {
      const ticker = item.tckr;
      const nombre = item.nombre;
      const objetivo = item.objetivo;
      const currentPrice = currentPrices[ticker]?.price;
      if (!currentPrice || !objetivo) continue;
      const prevPrice = prevPrices[ticker];
      if (!prevPrice) continue;
      const nowInObjective = currentPrice >= objetivo;
      const wasInObjective = prevPrice >= objetivo;
      if (nowInObjective && !wasInObjective) {
        this.addNotification({ticker, nombre, evento: 'entró_objetivo', precio: currentPrice, objetivo});
        newNotifications.push({ticker, evento: 'entró_objetivo'});
      } else if (!nowInObjective && wasInObjective) {
        this.addNotification({ticker, nombre, evento: 'salió_objetivo', precio: currentPrice, objetivo});
        newNotifications.push({ticker, evento: 'salió_objetivo'});
      }
      const distToObjective = (objetivo - currentPrice) / objetivo;
      const prevDistToObjective = (objetivo - prevPrice) / objetivo;
      const nowInPending = distToObjective >= 0 && distToObjective <= 0.07;
      const wasInPending = prevDistToObjective >= 0 && prevDistToObjective <= 0.07;
      if (nowInPending && !wasInPending) {
        this.addNotification({ticker, nombre, evento: 'entró_pendientes', precio: currentPrice});
        newNotifications.push({ticker, evento: 'entró_pendientes'});
      } else if (!nowInPending && wasInPending) {
        this.addNotification({ticker, nombre, evento: 'salió_pendientes', precio: currentPrice});
        newNotifications.push({ticker, evento: 'salió_pendientes'});
      }
    }
    this.savePreviousPrices(currentPrices);
    return newNotifications;
  }
  addNotification(data) {
    const hoy = this.getTodayDateString();
    const exists = this.notifications.some(n => n.ticker === data.ticker && n.evento === data.evento && n.fecha === hoy);
    if (exists) return;
    const notification = {
      id: Date.now(),
      ticker: data.ticker,
      nombre: data.nombre,
      evento: data.evento,
      precio: data.precio,
      hora: this.getTimeString(),
      fecha: hoy,
      semana: this.getWeekNumber(),
      timestamp: Date.now()
    };
    this.notifications.unshift(notification);
    this.saveNotifications();
    return notification;
  }
  getNotificationsToday() {
    const hoy = this.getTodayDateString();
    return this.notifications.filter(n => n.fecha === hoy);
  }
  getNotificationsThisWeek() {
    const semanaActual = this.getWeekNumber();
    return this.notifications.filter(n => n.semana === semanaActual);
  }
  getCountersToday() {
    const today = this.getNotificationsToday();
    return {
      entró_objetivo: today.filter(n => n.evento === 'entró_objetivo').length,
      salió_objetivo: today.filter(n => n.evento === 'salió_objetivo').length,
      entró_pendientes: today.filter(n => n.evento === 'entró_pendientes').length,
      salió_pendientes: today.filter(n => n.evento === 'salió_pendientes').length,
      total: today.length
    };
  }
  getCountersThisWeek() {
    const week = this.getNotificationsThisWeek();
    return {
      entró_objetivo: week.filter(n => n.evento === 'entró_objetivo').length,
      salió_objetivo: week.filter(n => n.evento === 'salió_objetivo').length,
      entró_pendientes: week.filter(n => n.evento === 'entró_pendientes').length,
      salió_pendientes: week.filter(n => n.evento === 'salió_pendientes').length,
      total: week.length
    };
  }
  cleanOldNotifications() {
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    this.notifications = this.notifications.filter(n => n.timestamp > thirtyDaysAgo);
    this.saveNotifications();
  }
  getTodayDateString() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
  getTimeString() {
    const d = new Date();
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  }
  getWeekNumber() {
    const d = new Date();
    const firstDay = new Date(d.getFullYear(), 0, 1);
    const pastDaysOfYear = (d - firstDay) / 86400000;
    return Math.ceil((pastDaysOfYear + firstDay.getDay() + 1) / 7);
  }
}
const notificationManager = new NotificationManager();
