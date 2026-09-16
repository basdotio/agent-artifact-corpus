/**
 * Page Component Template
 * Portfolio Frontend Design System
 *
 * Usage: Copy this template when creating new pages/routes.
 * Place in: src/pages/
 *
 * After creating:
 * 1. Add route to src/App.jsx
 * 2. Add to scripts/prerender.mjs for SEO
 * 3. Update public/sitemap.xml
 * 4. Create OG image in public/images/og/
 */

import SEO from '../components/seo/SEO';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import Breadcrumbs from '../components/ui/Breadcrumbs';
import { SITE_CONFIG } from '../utils/constants';

// Page transition variants
const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    y: -20,
    transition: { duration: 0.3 }
  }
};

const contentVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: 'easeOut' }
  }
};

const PageName = () => {
  // TODO: Update breadcrumb items
  const breadcrumbItems = [
    { label: 'Home', path: '/' },
    { label: 'Page Title', path: '/page-slug' }
  ];

  return (
    <>
      {/* SEO Meta Tags - TODO: Update all values.
          Head tags never go inline in a page: <SEO> owns title, description,
          canonical, hreflang, Open Graph and Twitter, and React 19 hoists them
          into <head> while committing the render. */}
      <SEO
        title="Page Title"
        description="Page description for SEO. 150-160 characters max, describing the page content clearly."
        path="/page-slug"
        image="/images/og/page-slug.webp"
      />

      <motion.main
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        className="min-h-screen pt-24 pb-16 px-4 md:px-8"
      >
        {/* Background decorations */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
          <div className="absolute top-1/4 -left-20 w-72 h-72 bg-green-500/5 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
        </div>

        <div className="max-w-4xl mx-auto">
          {/* Breadcrumbs */}
          <Breadcrumbs items={breadcrumbItems} />

          {/* Page Header */}
          <motion.header
            variants={contentVariants}
            initial="hidden"
            animate="visible"
            className="mb-12"
          >
            <motion.h1
              variants={itemVariants}
              className="text-4xl md:text-5xl font-bold mb-4"
            >
              {/* TODO: Update page title */}
              <span className="bg-gradient-to-r from-green-400 to-cyan-400 bg-clip-text text-transparent">
                Page Title
              </span>
            </motion.h1>
            <motion.p variants={itemVariants} className="text-gray-400 text-lg">
              {/* TODO: Update page subtitle */}
              Page subtitle or brief description goes here.
            </motion.p>
          </motion.header>

          {/* Page Content */}
          <motion.article
            variants={contentVariants}
            initial="hidden"
            animate="visible"
            className="prose prose-invert prose-green max-w-none"
          >
            {/* TODO: Add page content */}
            <motion.section variants={itemVariants}>
              <h2>Section Heading</h2>
              <p>
                Your page content goes here. Use semantic HTML and proper
                heading hierarchy.
              </p>
            </motion.section>

            <motion.section variants={itemVariants}>
              <h2>Another Section</h2>
              <p>More content for the page.</p>
            </motion.section>
          </motion.article>

          {/* Back Link */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-12"
          >
            <Link
              to="/"
              className="
                inline-flex items-center gap-2
                text-gray-400 hover:text-green-400
                transition-colors
              "
            >
              <span>&larr;</span>
              <span>Back to Home</span>
            </Link>
          </motion.div>
        </div>
      </motion.main>
    </>
  );
};

export default PageName;
