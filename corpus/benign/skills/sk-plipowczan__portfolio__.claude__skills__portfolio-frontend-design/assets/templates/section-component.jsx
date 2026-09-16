/**
 * Section Component Template
 * Portfolio Frontend Design System
 *
 * Usage: Copy this template when creating new homepage sections.
 * Place in: src/components/sections/
 *
 * Instructions:
 * 1. Copy this file to src/components/sections/
 * 2. Rename to match your section (e.g., Testimonials.jsx)
 * 3. Update component name, id, title, and content
 * 4. Import and add to Home.jsx
 */

import { motion } from 'framer-motion';

// Animation variants for staggered entry
const containerVariants = {
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

const SectionName = () => {
  // TODO: Replace with your data
  const items = [
    { id: 1, title: 'Item 1', description: 'Description for item 1' },
    { id: 2, title: 'Item 2', description: 'Description for item 2' },
    { id: 3, title: 'Item 3', description: 'Description for item 3' }
  ];

  return (
    <section
      id="section-id" // TODO: Update for smooth scroll navigation
      className="relative min-h-screen py-20 px-4 md:px-8 lg:px-16"
    >
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-72 h-72 bg-green-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.3 }}
          variants={containerVariants}
          className="text-center mb-16"
        >
          <motion.h2
            variants={itemVariants}
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-4"
          >
            {/* TODO: Update section title */}
            <span className="bg-gradient-to-r from-green-400 via-cyan-400 to-green-300 bg-clip-text text-transparent">
              Section Title
            </span>
          </motion.h2>
          <motion.p
            variants={itemVariants}
            className="text-gray-400 text-lg max-w-2xl mx-auto"
          >
            {/* TODO: Update section description */}
            Section description text goes here. Explain what this section is
            about.
          </motion.p>
        </motion.div>

        {/* Section Content - Grid Layout */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={containerVariants}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
        >
          {items.map((item) => (
            <motion.div
              key={item.id}
              variants={itemVariants}
              whileHover={{ y: -10 }}
              className="
                bg-white/5 backdrop-blur-sm
                border border-white/10 rounded-xl
                p-6
                transition-all duration-300
                hover:border-green-500/30
                hover:shadow-[0_0_30px_rgba(0,255,157,0.15)]
              "
            >
              {/* Item content */}
              <h3 className="text-xl font-semibold text-white mb-2">
                {item.title}
              </h3>
              <p className="text-gray-400">{item.description}</p>
            </motion.div>
          ))}
        </motion.div>

        {/* Optional: CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="text-center mt-12"
        >
          <button
            className="
              px-8 py-4
              bg-green-500 hover:bg-green-400
              text-black font-semibold
              rounded-lg
              transition-all duration-300
              hover:scale-105
              hover:shadow-[0_0_30px_rgba(0,255,157,0.3)]
            "
          >
            Call to Action
          </button>
        </motion.div>
      </div>
    </section>
  );
};

export default SectionName;
