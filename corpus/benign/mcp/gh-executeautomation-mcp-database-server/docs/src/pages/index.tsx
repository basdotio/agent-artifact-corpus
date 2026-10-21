import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className={styles.heroTitle}>
          {siteConfig.title}
        </Heading>
        <p className={styles.heroSubtitle}>{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className={clsx('button button--secondary button--lg', styles.button)}
            to="/docs/intro">
            Get Started with Database Server ⏱️
          </Link>
          <Link
            className={clsx('button button--outline button--lg', styles.button)}
            to="/docs/database-tools">
            View Database Tools
          </Link>
        </div>
      </div>
    </header>
  );
}

function DatabaseSupport() {
  return (
    <section className="padding-vert--xl">
      <div className="container">
        <div className="row">
          <div className="col col--8 col--offset-2 text--center">
            <Heading as="h2">Supported Databases</Heading>
            <p className="padding-vert--md">
              The MCP Database Server provides seamless integration with multiple database systems,
              allowing Claude to query and manipulate data with ease.
            </p>
          </div>
        </div>
        <div className="row padding-vert--lg">
          <div className="col col--4 text--center">
            <div className="padding--lg">
              <h3>SQLite</h3>
              <p>Perfect for local development and lightweight applications.</p>
            </div>
          </div>
          <div className="col col--4 text--center">
            <div className="padding--lg">
              <h3>SQL Server</h3>
              <p>Robust enterprise-grade database with powerful features.</p>
            </div>
          </div>
          <div className="col col--4 text--center">
            <div className="padding--lg">
              <h3>PostgreSQL</h3>
              <p>Advanced open-source database with extensive capabilities.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function CallToAction() {
  return (
    <section className={styles.callToAction}>
      <div className="container">
        <div className="row">
          <div className="col col--10 col--offset-1 text--center">
            <Heading as="h2">Ready to Connect Claude to Your Databases?</Heading>
            <p className="padding-vert--md">
              Start leveraging the power of AI with your structured data today.
              Follow our simple setup guide to get up and running in minutes.
            </p>
            <div className="padding-vert--md">
              <Link
                className="button button--primary button--lg"
                to="/docs/getting-started">
                Get Started Now
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Home(): JSX.Element {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title}`}
      description="Connect Claude to your databases with MCP Database Server">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
        <DatabaseSupport />
        <CallToAction />
      </main>
    </Layout>
  );
}
