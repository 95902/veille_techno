<?php

use App\Filament\Resources\Categories\CategoryResource;
use App\Filament\Resources\Categories\Pages\CreateCategory;
use App\Filament\Resources\Categories\Pages\EditCategory;
use App\Filament\Resources\Categories\Pages\ListCategories;
use App\Models\Article;
use App\Models\Category;
use App\Models\User;
use Filament\Actions\DeleteAction;
use Filament\Actions\Testing\TestAction;
use Illuminate\Validation\ValidationException;
use Livewire\Livewire;

beforeEach(function () {
    $this->actingAs(User::factory()->admin()->create());
});

test('a non-admin cannot reach the categories resource', function () {
    $category = Category::factory()->create();
    $this->actingAs(User::factory()->create());

    $this->get(CategoryResource::getUrl('index'))->assertForbidden();
    $this->get(CategoryResource::getUrl('create'))->assertForbidden();
    $this->get(CategoryResource::getUrl('edit', ['record' => $category]))->assertForbidden();
});

test('an admin creates a category with a description', function () {
    $this->get(CategoryResource::getUrl('index'))->assertOk();

    Livewire::test(CreateCategory::class)
        ->fillForm([
            'name' => 'Robotique',
            'slug' => 'robotique',
            'description' => 'Robots, IA incarnée.',
        ])
        ->call('create')
        ->assertHasNoFormErrors();

    $category = Category::where('slug', 'robotique')->sole();

    expect($category->description)->toBe('Robots, IA incarnée.');

    Livewire::test(ListCategories::class)->assertCanSeeTableRecords([$category]);
});

test('a slug must be lowercase kebab-case and unique', function () {
    Category::factory()->create(['slug' => 'modeles']);

    Livewire::test(CreateCategory::class)
        ->fillForm(['name' => 'X', 'slug' => 'Pas Valide'])
        ->call('create')
        ->assertHasFormErrors(['slug' => 'regex']);

    Livewire::test(CreateCategory::class)
        ->fillForm(['name' => 'X', 'slug' => 'modeles'])
        ->call('create')
        ->assertHasFormErrors(['slug' => 'unique']);
});

test('an admin edits a category', function () {
    $category = Category::factory()->create();

    Livewire::test(EditCategory::class, ['record' => $category->getRouteKey()])
        ->fillForm(['name' => 'Renommée', 'description' => 'Nouvelle consigne.'])
        ->call('save')
        ->assertHasNoFormErrors();

    expect($category->refresh()->name)->toBe('Renommée')
        ->and($category->description)->toBe('Nouvelle consigne.');
});

test('an admin deletes an unused category', function () {
    $category = Category::factory()->create();

    Livewire::test(ListCategories::class)
        ->callAction(TestAction::make(DeleteAction::class)->table($category));

    $this->assertModelMissing($category);
});

test('a category used by articles cannot be deleted from the table', function () {
    $category = Category::factory()->create();
    Article::factory()->create(['category_id' => $category->id]);

    Livewire::test(ListCategories::class)
        ->callAction(TestAction::make(DeleteAction::class)->table($category))
        ->assertNotified('Suppression impossible');

    $this->assertModelExists($category);
});

test('a category used by articles cannot be deleted from the edit page', function () {
    $category = Category::factory()->create();
    Article::factory()->create(['category_id' => $category->id]);

    Livewire::test(EditCategory::class, ['record' => $category->getRouteKey()])
        ->callAction(DeleteAction::class)
        ->assertNotified('Suppression impossible');

    $this->assertModelExists($category);
});

test('the model refuses to delete a used category outside the back-office', function () {
    $category = Category::factory()->create();
    Article::factory()->create(['category_id' => $category->id]);

    expect(fn () => $category->delete())->toThrow(ValidationException::class, Category::IN_USE_MESSAGE);

    $this->assertModelExists($category);
});
