import styles from './page.module.css';

export default function Home() {
  return (
    <main className={styles.page}>
      <div className={styles.glow} />

      <nav className={styles.nav}>
        <div className={styles.logo}>
          e-Sim<span className={styles.logoDot}>.</span>
        </div>
        <div className={styles.navLinks}>
          <a href="#features" className={styles.navLink}>Features</a>
          <a href="#destinations" className={styles.navLink}>Destinations</a>
          <a href="#pricing" className={styles.navLink}>Pricing</a>
          <a href="http://localhost:8000/auth/google/login" className={styles.navLink}>Log in</a>
          <a href="http://localhost:8000/auth/google/login" className={styles.primaryBtn} style={{ display: 'inline-block', lineHeight: 'normal' }}>
            Get Started
          </a>
        </div>
      </nav>

      <section className={styles.hero}>
        <div className={styles.badge}>Next-Gen Connectivity</div>
        <h1 className={styles.title}>
          The world&apos;s data, <span className="gradient-text">in your pocket.</span>
        </h1>
        <p className={styles.subtitle}>
          Instantly connect to local networks in over 150+ countries. No physical SIM needed, roaming charges are a thing of the past.
        </p>
        <div className={styles.ctaGroup}>
          <a href="http://localhost:8000/auth/google/login" className={`${styles.primaryBtn} ${styles.largeBtn}`} style={{ display: 'inline-flex', alignItems: 'center' }}>
            Connect Now
          </a>
          <a href="#plans" className={styles.secondaryBtn}>
            View Plans
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>
      </section>

      <section id="features" className={styles.features}>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🌍</div>
          <h3 className={styles.featureTitle}>Global Coverage</h3>
          <p className={styles.featureDesc}>Get high-speed 5G/4G connectivity automatically switching to the best local networks across the globe.</p>
        </div>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>⚡</div>
          <h3 className={styles.featureTitle}>Instant Activation</h3>
          <p className={styles.featureDesc}>Scan a QR code to download your eSIM directly to your device and get online in seconds.</p>
        </div>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>🛡️</div>
          <h3 className={styles.featureTitle}>No Hidden Fees</h3>
          <p className={styles.featureDesc}>Transparent pricing with zero roaming charges. Pay for what you need exactly when you need it.</p>
        </div>
      </section>
    </main>
  );
}
