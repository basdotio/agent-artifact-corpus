/**
 * Card Component Template
 * Portfolio Frontend Design System
 *
 * Usage: Copy this template for card-based content.
 * Place in: src/components/ui/
 *
 * Features:
 * - Glassmorphism styling
 * - Hover effects (lift + glow)
 * - Responsive image
 * - Tags support
 * - Link or onClick support
 * - PropTypes validation
 */

import { motion } from 'framer-motion';
import PropTypes from 'prop-types';

// Animation variants
const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: 'easeOut' }
  }
};

const Card = ({
  title,
  description,
  image,
  imageAlt,
  tags = [],
  link,
  linkExternal = false,
  onClick,
  featured = false,
  className = ''
}) => {
  // Determine wrapper element based on interaction type
  const isClickable = link || onClick;
  const CardWrapper = link ? 'a' : 'div';

  // Props for wrapper element
  const wrapperProps = link
    ? {
        href: link,
        target: linkExternal ? '_blank' : undefined,
        rel: linkExternal ? 'noopener noreferrer' : undefined
      }
    : onClick
      ? { onClick, role: 'button', tabIndex: 0 }
      : {};

  // Handle keyboard activation for non-link clickable cards
  const handleKeyDown = (e) => {
    if (onClick && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <motion.div
      variants={cardVariants}
      whileHover={isClickable ? { y: -10 } : undefined}
      transition={{ type: 'spring', stiffness: 300 }}
      className={className}
    >
      <CardWrapper
        {...wrapperProps}
        onKeyDown={onClick ? handleKeyDown : undefined}
        className={`
          block group
          ${isClickable ? 'cursor-pointer' : ''}
        `}
      >
        <div
          className={`
            relative overflow-hidden rounded-xl
            bg-white/5 backdrop-blur-sm
            border transition-all duration-300
            ${featured ? 'border-green-500/30' : 'border-white/10'}
            ${isClickable ? 'hover:border-green-500/30 hover:shadow-[0_0_30px_rgba(0,255,157,0.15)]' : ''}
          `}
        >
          {/* Featured Badge */}
          {featured && (
            <div className="absolute top-4 right-4 z-10">
              <span
                className="
                  px-3 py-1 text-xs font-medium
                  bg-green-500/20 text-green-400
                  rounded-full border border-green-500/30
                "
              >
                Featured
              </span>
            </div>
          )}

          {/* Image */}
          {image && (
            <div className="aspect-video overflow-hidden">
              <img
                src={image}
                alt={imageAlt || title}
                loading="lazy"
                className={`
                  w-full h-full object-cover
                  transition-transform duration-500
                  ${isClickable ? 'group-hover:scale-105' : ''}
                `}
              />
            </div>
          )}

          {/* Content */}
          <div className="p-6">
            {/* Title */}
            <h3
              className={`
                text-xl font-semibold text-white mb-2
                transition-colors
                ${isClickable ? 'group-hover:text-green-400' : ''}
              `}
            >
              {title}
            </h3>

            {/* Description */}
            {description && (
              <p className="text-gray-400 text-sm mb-4 line-clamp-2">
                {description}
              </p>
            )}

            {/* Tags */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {tags.map((tag, index) => (
                  <span
                    key={index}
                    className="
                      px-2 py-1 text-xs rounded-full
                      bg-green-500/10 text-green-400
                      border border-green-500/20
                    "
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardWrapper>
    </motion.div>
  );
};

Card.propTypes = {
  /** Card title - required */
  title: PropTypes.string.isRequired,
  /** Card description */
  description: PropTypes.string,
  /** Image URL */
  image: PropTypes.string,
  /** Image alt text (defaults to title if not provided) */
  imageAlt: PropTypes.string,
  /** Array of tag strings */
  tags: PropTypes.arrayOf(PropTypes.string),
  /** Link URL - makes card a link */
  link: PropTypes.string,
  /** Whether link opens in new tab */
  linkExternal: PropTypes.bool,
  /** Click handler - makes card clickable button */
  onClick: PropTypes.func,
  /** Whether to show featured badge */
  featured: PropTypes.bool,
  /** Additional CSS classes */
  className: PropTypes.string
};

export default Card;

/**
 * Usage Examples:
 *
 * // Basic card
 * <Card
 *   title="Project Name"
 *   description="Project description"
 *   image="/images/project.jpg"
 *   tags={['React', 'Tailwind']}
 * />
 *
 * // Clickable card with external link
 * <Card
 *   title="View on GitHub"
 *   description="Check out the source code"
 *   link="https://github.com/..."
 *   linkExternal
 *   tags={['Open Source']}
 * />
 *
 * // Featured card with onClick
 * <Card
 *   title="Featured Project"
 *   description="Our best work"
 *   image="/images/featured.jpg"
 *   featured
 *   onClick={() => openModal('project-1')}
 * />
 *
 * // In a grid with staggered animation
 * <motion.div
 *   initial="hidden"
 *   whileInView="visible"
 *   variants={containerVariants}
 *   className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
 * >
 *   {projects.map((project) => (
 *     <Card key={project.id} {...project} />
 *   ))}
 * </motion.div>
 */
