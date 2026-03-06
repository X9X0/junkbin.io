import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recipes, junkbin } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import EditRecipeModal from '../components/EditRecipeModal';
import MatchPercentageBar from '../components/MatchPercentageBar';
import {
  Cpu,
  Clock,
  ExternalLink,
  Check,
  X,
  Plus,
  Eye,
  ArrowLeft,
  Pencil,
  Trash2,
} from 'lucide-react';
import clsx from 'clsx';
import { useState } from 'react';
import LazyImage from '../components/LazyImage';

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'text-cyber-green border-cyber-green',
  intermediate: 'text-cyber-cyan border-cyber-cyan',
  advanced: 'text-cyber-yellow border-cyber-yellow',
  expert: 'text-cyber-pink border-cyber-pink',
};

export default function RecipeDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [addingToWantList, setAddingToWantList] = useState<string | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: recipe, isLoading } = useQuery({
    queryKey: ['recipe', id],
    queryFn: () => recipes.get(id!),
    enabled: !!id,
  });

  const { data: matchData } = useQuery({
    queryKey: ['recipe', id, 'match'],
    queryFn: () => recipes.match(id!),
    enabled: !!id && isAuthenticated,
  });

  const addToWantList = useMutation({
    mutationFn: (componentId: string) =>
      junkbin.create({
        content_type: 'component',
        object_id: componentId,
        item_type: 'want',
      }),
    onSuccess: () => {
      setAddingToWantList(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => recipes.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recipes'] });
      navigate('/recipes');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-cyber-cyan font-mono animate-pulse">
          {t('recipe_detail.loading')}
        </div>
      </div>
    );
  }

  if (!recipe) {
    return (
      <div className="py-20 text-center">
        <h2 className="font-display text-2xl text-white mb-4">{t('recipe_detail.not_found_title')}</h2>
        <Link to="/recipes" className="btn-cyber">
          {t('recipe_detail.back_recipes')}
        </Link>
      </div>
    );
  }

  const matchMap = new Map(
    matchData?.components?.map((c) => [c.component_id, c]) || []
  );

  return (
    <div className="py-8">
      <div className="mx-auto max-w-screen-2xl px-4">
        {/* Back link */}
        <Link
          to="/recipes"
          className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-cyber-cyan mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('recipe_detail.back')}
        </Link>

        {/* Hero Section */}
        <div className="card-cyber p-6 mb-6">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Image */}
            {recipe.image && (
              <div className="lg:w-1/3 aspect-video bg-cyber-black border border-cyber-light/20 overflow-hidden flex-shrink-0">
                <LazyImage
                  src={recipe.image}
                  alt={recipe.name}
                  className="w-full h-full object-cover"
                  fallback={<Cpu className="h-12 w-12 text-gray-600" />}
                />
              </div>
            )}

            {/* Info */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <span className="badge-cyber text-gray-400 border-gray-600">
                  {recipe.category_display || recipe.category}
                </span>
                <span
                  className={clsx(
                    'badge-cyber',
                    DIFFICULTY_COLORS[recipe.difficulty] || 'text-gray-400 border-gray-600'
                  )}
                >
                  {recipe.difficulty_display || recipe.difficulty}
                </span>
                {recipe.is_featured && (
                  <span className="badge-cyber text-cyber-yellow border-cyber-yellow">
                    {t('recipe_detail.featured')}
                  </span>
                )}
                {!recipe.is_approved && (
                  <span className="badge-cyber text-cyber-pink border-cyber-pink">
                    {t('recipe_detail.pending')}
                  </span>
                )}
              </div>

              <h1 className="font-display text-2xl lg:text-3xl font-bold text-white mb-3">
                {recipe.name}
              </h1>

              <p className="text-gray-400 mb-4 whitespace-pre-line">
                {recipe.description}
              </p>

              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                <span className="flex items-center gap-1">
                  <Cpu className="h-4 w-4" />
                  {t('recipe_detail.parts_count', { count: recipe.component_count })}
                </span>
                {recipe.estimated_time && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {recipe.estimated_time}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Eye className="h-4 w-4" />
                  {recipe.view_count} {t('recipe_detail.views')}
                </span>
                {recipe.created_by && (
                  <Link
                    to={`/users/${recipe.created_by.id}`}
                    className="text-cyber-cyan hover:underline"
                  >
                    by {recipe.created_by.username}
                  </Link>
                )}
              </div>

              {recipe.external_url && (
                <a
                  href={recipe.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-4 text-cyber-cyan hover:text-cyber-cyan/80 text-sm"
                >
                  <ExternalLink className="h-4 w-4" />
                  {t('recipe_detail.view_tutorial')}
                </a>
              )}

              {isAuthenticated && (user?.is_staff || recipe.created_by?.id === user?.id) && (
                <div className="flex items-center gap-3 mt-4">
                  <button
                    onClick={() => setShowEditModal(true)}
                    className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                  >
                    <Pencil className="h-4 w-4" />
                    {t('recipe_detail.edit_recipe')}
                  </button>
                  {!confirmDelete ? (
                    <button
                      onClick={() => setConfirmDelete(true)}
                      className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-cyber-pink transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                      {t('recipe_detail.delete_recipe')}
                    </button>
                  ) : (
                    <span className="inline-flex items-center gap-2 text-sm">
                      <span className="text-cyber-pink">{t('recipe_detail.are_you_sure')}</span>
                      <button
                        onClick={() => deleteMutation.mutate()}
                        disabled={deleteMutation.isPending}
                        className="text-cyber-pink hover:text-white font-mono text-xs border border-cyber-pink/50 px-2 py-0.5"
                      >
                        {deleteMutation.isPending ? t('recipe_detail.deleting') : t('recipe_detail.confirm_yes')}
                      </button>
                      <button
                        onClick={() => setConfirmDelete(false)}
                        className="text-gray-500 hover:text-white font-mono text-xs"
                      >
                        {t('common.cancel')}
                      </button>
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Match summary for authenticated users */}
          {isAuthenticated && matchData && (
            <div className="mt-6 pt-6 border-t border-cyber-light/20">
              <div className="flex items-center gap-4 mb-2">
                <span className="text-sm font-mono text-gray-400">
                  {t('recipe_detail.match_count', { matched: matchData.matched_count, total: matchData.total_required })}
                </span>
              </div>
              <MatchPercentageBar percentage={matchData.match_percentage} />
            </div>
          )}

          {!isAuthenticated && (
            <div className="mt-6 pt-6 border-t border-cyber-light/20">
              <p className="text-sm text-gray-500">
                <Link to="/login" className="text-cyber-cyan hover:underline">
                  {t('common.log_in')}
                </Link>{' '}
                {t('recipe_detail.login_for_junkbin')}
              </p>
            </div>
          )}
        </div>

        {/* BOM Table */}
        <div className="card-cyber p-6">
          <h2 className="font-display text-xl font-bold text-white mb-4">
            {t('recipe_detail.bom_title')}
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-cyber-light/30">
                  {isAuthenticated && matchData && (
                    <th className="text-left py-3 px-2 text-gray-500 font-mono text-xs w-10">
                      {t('recipe_detail.col_have')}
                    </th>
                  )}
                  <th className="text-left py-3 px-2 text-gray-500 font-mono text-xs">
                    {t('recipe_detail.col_part')}
                  </th>
                  <th className="text-left py-3 px-2 text-gray-500 font-mono text-xs">
                    {t('recipe_detail.col_manufacturer')}
                  </th>
                  <th className="text-left py-3 px-2 text-gray-500 font-mono text-xs">
                    {t('recipe_detail.col_type')}
                  </th>
                  <th className="text-left py-3 px-2 text-gray-500 font-mono text-xs">
                    {t('recipe_detail.col_value')}
                  </th>
                  <th className="text-center py-3 px-2 text-gray-500 font-mono text-xs">
                    {t('recipe_detail.col_qty')}
                  </th>
                  <th className="text-left py-3 px-2 text-gray-500 font-mono text-xs">
                    {t('recipe_detail.col_notes')}
                  </th>
                  {isAuthenticated && matchData && (
                    <th className="text-right py-3 px-2 text-gray-500 font-mono text-xs">
                      {t('recipe_detail.col_action')}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {recipe.bom?.map((item) => {
                  const matched = matchMap.get(item.component_id);
                  const userHas = matched?.user_has ?? false;
                  const availableFrom = matched?.available_from || [];

                  return (
                    <tr
                      key={item.id}
                      className={clsx(
                        'border-b border-cyber-light/10 hover:bg-cyber-light/5',
                        item.is_optional && 'opacity-60'
                      )}
                    >
                      {isAuthenticated && matchData && (
                        <td className="py-3 px-2">
                          {userHas ? (
                            <Check className="h-4 w-4 text-cyber-green" />
                          ) : (
                            <X className="h-4 w-4 text-cyber-pink" />
                          )}
                        </td>
                      )}
                      <td className="py-3 px-2">
                        <Link
                          to={`/components/${item.component_id}/products`}
                          className="text-cyber-cyan hover:underline font-mono"
                        >
                          {item.part_number}
                        </Link>
                        {item.is_optional && (
                          <span className="ml-2 text-[10px] text-gray-500 border border-gray-600 px-1">
                            {t('recipe_detail.optional')}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-2 text-gray-400">
                        {item.manufacturer}
                      </td>
                      <td className="py-3 px-2 text-gray-400">
                        {item.component_type_display || item.component_type}
                      </td>
                      <td className="py-3 px-2 text-gray-400 font-mono">
                        {item.primary_value || '—'}
                      </td>
                      <td className="py-3 px-2 text-center text-gray-400">
                        {item.quantity}
                      </td>
                      <td className="py-3 px-2 text-gray-500 text-xs">
                        {item.notes}
                      </td>
                      {isAuthenticated && matchData && (
                        <td className="py-3 px-2 text-right">
                          {!userHas && (
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  setAddingToWantList(item.component_id);
                                  addToWantList.mutate(item.component_id);
                                }}
                                disabled={addingToWantList === item.component_id}
                                className="text-[10px] text-cyber-cyan hover:text-cyber-cyan/80 border border-cyber-cyan/30 px-2 py-0.5 hover:bg-cyber-cyan/10 transition-colors"
                              >
                                <Plus className="h-3 w-3 inline mr-0.5" />
                                {t('recipe_detail.want_btn')}
                              </button>
                              {availableFrom.length > 0 && (
                                <span className="text-[10px] text-cyber-green">
                                  {t('recipe_detail.available_count', { count: availableFrom.length })}
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Available from section for missing parts */}
          {isAuthenticated && matchData && (
            <div className="mt-6">
              {matchData.components
                .filter((c) => !c.user_has && c.available_from.length > 0)
                .length > 0 && (
                <div className="border-t border-cyber-light/20 pt-4">
                  <h3 className="text-sm font-mono text-gray-400 mb-3">
                    {t('recipe_detail.missing_parts')}
                  </h3>
                  <div className="space-y-2">
                    {matchData.components
                      .filter((c) => !c.user_has && c.available_from.length > 0)
                      .map((c) => (
                        <div
                          key={c.component_id}
                          className="flex items-center gap-3 text-sm"
                        >
                          <span className="text-gray-400 font-mono min-w-[120px]">
                            {c.part_number}
                          </span>
                          <span className="text-gray-500">{t('recipe_detail.available_from')}</span>
                          {c.available_from.map((u) => (
                            <Link
                              key={u.user_id}
                              to={`/users/${u.user_id}`}
                              className="text-cyber-cyan hover:underline text-xs"
                            >
                              {u.username} ({u.quantity}x, {u.condition})
                            </Link>
                          ))}
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Edit Recipe Modal */}
      {recipe && (
        <EditRecipeModal
          recipe={recipe}
          isOpen={showEditModal}
          onClose={() => setShowEditModal(false)}
          isStaff={user?.is_staff || false}
        />
      )}
    </div>
  );
}
