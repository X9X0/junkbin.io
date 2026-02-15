import { Link } from 'react-router-dom';
import { Clock, Cpu, ExternalLink } from 'lucide-react';
import clsx from 'clsx';
import type { Recipe } from '../types';
import MatchPercentageBar from './MatchPercentageBar';
import LazyImage from './LazyImage';

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'text-cyber-green border-cyber-green',
  intermediate: 'text-cyber-cyan border-cyber-cyan',
  advanced: 'text-cyber-yellow border-cyber-yellow',
  expert: 'text-cyber-pink border-cyber-pink',
};

interface RecipeCardProps {
  recipe: Recipe;
  showMatch?: boolean;
}

export default function RecipeCard({ recipe, showMatch = false }: RecipeCardProps) {
  return (
    <Link
      to={`/recipes/${recipe.id}`}
      className="card-cyber hover:border-cyber-cyan/50 transition-all group p-4"
    >
      {/* Image */}
      <div className="aspect-video mb-4 bg-cyber-black flex items-center justify-center border border-cyber-light/20 overflow-hidden">
        {recipe.image ? (
          <LazyImage
            src={recipe.image}
            alt={recipe.name}
            className="w-full h-full object-cover"
            fallback={<Cpu className="h-8 w-8 text-gray-600" />}
          />
        ) : (
          <Cpu className="h-8 w-8 text-gray-600" />
        )}
      </div>

      {/* Category + Difficulty badges */}
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <span className="badge-cyber text-gray-400 border-gray-600 text-[10px]">
          {recipe.category_display || recipe.category}
        </span>
        <span
          className={clsx(
            'badge-cyber text-[10px]',
            DIFFICULTY_COLORS[recipe.difficulty] || 'text-gray-400 border-gray-600'
          )}
        >
          {recipe.difficulty_display || recipe.difficulty}
        </span>
        {recipe.is_featured && (
          <span className="badge-cyber text-cyber-yellow border-cyber-yellow text-[10px]">
            FEATURED
          </span>
        )}
      </div>

      {/* Name */}
      <h3 className="font-semibold text-white group-hover:text-cyber-cyan transition-colors line-clamp-2 mb-2">
        {recipe.name}
      </h3>

      {/* Description */}
      <p className="text-sm text-gray-400 line-clamp-2 mb-3">
        {recipe.description}
      </p>

      {/* Stats row */}
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <Cpu className="h-3 w-3" />
          {recipe.component_count} parts
        </span>
        {recipe.estimated_time && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {recipe.estimated_time}
          </span>
        )}
        {recipe.external_url && (
          <ExternalLink className="h-3 w-3 text-cyber-cyan" />
        )}
      </div>

      {/* Match percentage bar */}
      {showMatch && recipe.match_percentage != null && (
        <div className="mt-3 pt-3 border-t border-cyber-light/20">
          <MatchPercentageBar percentage={recipe.match_percentage} />
        </div>
      )}
    </Link>
  );
}
