import pytest

from wardrobe_rag.constraints import assemble_outfit, validate_selection
from wardrobe_rag.query_attributes import attribute_violations, query_conditions
from wardrobe_rag.schemas import RetrievalRequest, SlotSearchRequest
from test_retrieval import ControlledStore, engine_for


def test_scoped_constraints_keep_unrelated_leather_and_prefer_wool(embedder, make_item):
    items = [
        make_item('shirt'), make_item('pants', 'bottoms', 'Брюки'),
        make_item('leather-shoe', 'shoes', 'Кроссовки', color='Чёрный', material='100% кожа'),
        make_item('unknown-shoe', 'shoes', 'Кроссовки', color='Чёрный', material=None),
        make_item('good-shoe', 'shoes', 'Кроссовки', color='Графит', material='Полиэстер'),
        make_item('wrong-coat', 'outerwear', 'Пальто', color='Чёрный', material='Шерсть'),
        make_item('cotton-coat', 'outerwear', 'Пальто', color='Бежевый', material='Хлопок'),
        make_item('wool-coat', 'outerwear', 'Пальто', color='Бежевый', material='Шерсть'),
        make_item('bag', 'accessories', 'Сумка', color='Коричневый', material='Кожа'),
    ]
    request = RetrievalRequest(user_id='alice', query=(
        'Собери образ: тёмные кроссовки без кожи, а к ним бежевое пальто, желательно из шерсти '
        'и коричневая сумка из кожи.'
    ))
    engine = engine_for(ControlledStore({'alice': items}), embedder)
    result = engine.retrieve(request)
    assert [row.item_id for row in result.candidates_by_slot['shoes']] == ['good-shoe']
    assert [row.item_id for row in result.candidates_by_slot['outerwear']] == ['wool-coat', 'cotton-coat']
    assert {item.id for item in assemble_outfit(result).selected_items} == {'shirt', 'pants', 'good-shoe', 'wool-coat', 'bag'}
    assert not validate_selection(['shirt', 'pants', 'leather-shoe', 'wool-coat', 'bag'], result).valid


@pytest.mark.parametrize(('query', 'accepted'), [
    ('пальто с хлопковым верхом и вискозной подкладкой', {'coat-ok'}),
    ('пальто, в подкладке не должно быть шерсти', {'coat-ok'}),
    ('пальто с подкладкой не менее 97.5% вискозы', {'coat-ok'}),
    ('пальто вообще без шерсти', set()),
])
def test_material_evidence_is_component_specific(query, accepted, make_item):
    items = [
        make_item('coat-ok', 'outerwear', 'Пальто', material='100% хлопок', materialDetails={'lining': '97,5% вискоза, 2,5% эластан'}),
        make_item('coat-wool', 'outerwear', 'Пальто', material='100% хлопок', materialDetails={'lining': '100% шерсть'}),
        make_item('coat-unknown', 'outerwear', 'Пальто', material='100% хлопок'),
    ]
    assert {item.id for item in items if not attribute_violations(item, query_conditions(query))} == accepted


def test_slot_replacement_checks_lining_without_changing_kept_items(embedder, make_item):
    items = [
        make_item('shirt'), make_item('old', 'shoes', 'Туфли'),
        make_item('lined', 'shoes', 'Кроссовки', material='Хлопок', materialDetails={'lining': 'Кожа'}),
        make_item('textile', 'shoes', 'Кроссовки', material='Хлопок', materialDetails={'lining': 'Вискоза'}),
    ]
    result = engine_for(ControlledStore({'alice': items}), embedder).retrieve_slot(SlotSearchRequest(
        user_id='alice', query='Замени туфли на кроссовки без кожи в подкладке',
        slot='shoes', operation='replace', outfit_item_ids=['shirt', 'old'],
    ))
    assert [row.item_id for row in result.candidates] == ['textile']
    assert result.kept_item_ids == ['shirt']
