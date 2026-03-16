import styles from './page.module.css';

export default function Home() {
  return (
    <main className={styles.page}>
      <div className={styles.glow} />

      <nav className={styles.nav}>
        <div className={styles.logo}>
          E-Sim<span className={styles.logoDot}>.</span>
        </div>
        <div className={styles.navLinks}>
          <a href="#features" className={styles.navLink}>Features</a>
          <a href="/documents" className={styles.navLink}>Projects</a>
          <a href="#about" className={styles.navLink}>About</a>
          <a href="http://localhost:8000/auth/google/login" className={styles.navLink}>Log in</a>
          <a href="http://localhost:8000/auth/google/login" className={styles.primaryBtn} style={{ display: 'inline-block', lineHeight: 'normal' }}>
            Get Started
          </a>
        </div>
      </nav>

      <section className={styles.hero}>
        <div className={styles.badge}>Electronic Simulator</div>
        <h1 className={styles.title}>
          Design, <span className="gradient-text">simulate instantly.</span>
        </h1>
        <p className={styles.subtitle}>
          Build, test, and simulate electronic systems right in your browser. Powered by a WASM-based engine for real-time feedback.
        </p>
        <div className={styles.ctaGroup}>
          <a href="http://localhost:8000/auth/google/login" className={`${styles.primaryBtn} ${styles.largeBtn}`} style={{ display: 'inline-flex', alignItems: 'center' }}>
            Get Started
          </a>
          <a href="#features" className={styles.secondaryBtn}>
            Learn More
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>
      </section>

      <section id="features" className={styles.features}>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>⚡</div>
          <h3 className={styles.featureTitle}>WASM-Powered Editor</h3>
          <p className={styles.featureDesc}>Write and edit system descriptions with our C++-compiled WebAssembly text editor for blazing-fast performance.</p>
        </div>
        <div className={styles.featureCard}>
          <div className={styles.featureIcon}>☁️</div>
          <h3 className={styles.featureTitle}>Google Drive Sync</h3>
          <p className={styles.featureDesc}>Save your projects directly to Google Drive. Access and edit them from anywhere, on any device.</p>
        </div>
      </section>
    </main>
  );
}
