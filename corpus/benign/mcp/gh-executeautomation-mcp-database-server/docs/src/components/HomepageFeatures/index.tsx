import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: JSX.Element;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Easy to Use',
    Svg: require('@site/static/img/easy-to-use.svg').default,
    description: (
      <>
        MCP Database Server is easy to configure. Just update your Claude Desktop config file, and you're ready to start querying your databases!
      </>
    ),
  },
  {
    title: 'Multiple Database Support',
    Svg: require('@site/static/img/mcp-database.svg').default,
    description: (
      <>
        Seamlessly connect to <code>SQLite</code>, <code>SQL Server</code>, and <code>PostgreSQL</code> databases with a consistent interface for all your data needs.
      </>
    ),
  },
  {
    title: 'Powered by Node.js',
    Svg: require('@site/static/img/node.svg').default,
    description: (
      <>
        Built with Node.js for high performance and reliability. Benefit from connection pooling, async operations, and efficient memory management.
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className={styles.featureItem}>
        <div className="text--center">
          <Svg className={styles.featureSvg} role="img" />
        </div>
        <div className="text--center">
          <Heading as="h3" className={styles.featureTitle}>{title}</Heading>
          <p className={styles.featureDescription}>{description}</p>
        </div>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): JSX.Element {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          <div className="col col--12 text--center">
            <Heading as="h2">Key Features</Heading>
            <p style={{marginBottom: '3rem'}}>Powerful capabilities to enhance your Claude interactions with databases</p>
          </div>
        </div>
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
