# Rails Pattern Reference

**Purpose**: Defines search strategies for common Rails patterns

**Version**: 1.0.0

---

## Service Layer Patterns

### Service Objects

```yaml
service_objects:
  title: "Service Objects"
  description: "Encapsulate business logic outside of models/controllers"
  search_paths:
    - "app/services/**/*.rb"
    - "app/lib/services/**/*.rb"
  file_patterns:
    - "*_service.rb"
  code_patterns:
    - "class \\w+Service"
    - "def call"
    - "def initialize"
  usage_patterns:
    - "\\w+Service\\.new"
    - "\\w+Service\\.call"
  test_paths:
    - "spec/services/**/*_spec.rb"
    - "test/services/**/*_test.rb"
  keywords: [service, business logic, use case, interactor]
  best_practice: |
    class UserRegistrationService
      def initialize(params)
        @params = params
      end

      def call
        ActiveRecord::Base.transaction do
          user = create_user
          send_welcome_email(user)
          notify_admin(user)
          user
        end
      end

      private

      def create_user
        User.create!(@params)
      end

      def send_welcome_email(user)
        UserMailer.welcome(user).deliver_later
      end

      def notify_admin(user)
        AdminMailer.new_user(user).deliver_later
      end
    end
```

### Form Objects

```yaml
form_objects:
  title: "Form Objects"
  description: "Handle complex form logic with multiple models"
  search_paths:
    - "app/forms/**/*.rb"
    - "app/lib/forms/**/*.rb"
  file_patterns:
    - "*_form.rb"
  code_patterns:
    - "class \\w+Form"
    - "include ActiveModel::Model"
    - "attr_accessor"
    - "validate"
  keywords: [form, multi-model, virtual attributes]
  best_practice: |
    class RegistrationForm
      include ActiveModel::Model

      attr_accessor :email, :password, :company_name

      validates :email, presence: true, format: { with: URI::MailTo::EMAIL_REGEXP }
      validates :password, presence: true, length: { minimum: 8 }
      validates :company_name, presence: true

      def save
        return false unless valid?

        ActiveRecord::Base.transaction do
          user = User.create!(email: email, password: password)
          Company.create!(name: company_name, owner: user)
        end
      end
    end
```

### Query Objects

```yaml
query_objects:
  title: "Query Objects"
  description: "Encapsulate complex database queries"
  search_paths:
    - "app/queries/**/*.rb"
    - "app/lib/queries/**/*.rb"
  file_patterns:
    - "*_query.rb"
  code_patterns:
    - "class \\w+Query"
    - "def initialize.*relation"
    - "def call"
    - "def resolve"
  keywords: [query, scope, filtering, search]
  best_practice: |
    class ActiveUsersQuery
      def initialize(relation = User.all)
        @relation = relation
      end

      def call
        @relation
          .where(active: true)
          .where("last_login_at > ?", 30.days.ago)
          .order(created_at: :desc)
      end
    end

    # Usage:
    ActiveUsersQuery.new.call
    ActiveUsersQuery.new(User.where(role: 'admin')).call
```

---

## Model Patterns

### Concerns

```yaml
concerns:
  title: "Model Concerns"
  description: "Shared behavior across models"
  search_paths:
    - "app/models/concerns/**/*.rb"
  file_patterns:
    - "*.rb"
  code_patterns:
    - "module \\w+"
    - "extend ActiveSupport::Concern"
    - "included do"
    - "class_methods do"
  keywords: [concern, mixin, shared behavior]
  best_practice: |
    module Taggable
      extend ActiveSupport::Concern

      included do
        has_many :taggings, as: :taggable
        has_many :tags, through: :taggings

        scope :tagged_with, ->(tag_name) {
          joins(:tags).where(tags: { name: tag_name })
        }
      end

      def tag_list
        tags.pluck(:name).join(', ')
      end

      class_methods do
        def most_tagged
          joins(:taggings).group('id').order('COUNT(taggings.id) DESC')
        end
      end
    end
```

### Scopes

```yaml
scopes:
  title: "Named Scopes"
  description: "Reusable query methods"
  search_paths:
    - "app/models/**/*.rb"
  code_patterns:
    - "scope :\\w+,"
    - "scope :\\w+, ->"
  keywords: [scope, query, filter]
  best_practice: |
    class User < ApplicationRecord
      scope :active, -> { where(active: true) }
      scope :admin, -> { where(role: 'admin') }
      scope :recent, -> { where("created_at > ?", 30.days.ago) }
      scope :search, ->(query) { where("name ILIKE ?", "%#{query}%") }

      # Chainable scopes
      scope :with_posts, -> { joins(:posts).distinct }
      scope :popular, -> { where("followers_count > ?", 100) }
    end

    # Usage:
    User.active.admin.recent
```

### Polymorphic Associations

```yaml
polymorphic_associations:
  title: "Polymorphic Associations"
  description: "Flexible belongs_to relationships"
  search_paths:
    - "app/models/**/*.rb"
  code_patterns:
    - "belongs_to :\\w+, polymorphic: true"
    - "has_many :\\w+, as:"
  keywords: [polymorphic, flexible association]
  best_practice: |
    # Polymorphic model
    class Comment < ApplicationRecord
      belongs_to :commentable, polymorphic: true
    end

    # Models that can have comments
    class Post < ApplicationRecord
      has_many :comments, as: :commentable
    end

    class Photo < ApplicationRecord
      has_many :comments, as: :commentable
    end

    # Migration
    create_table :comments do |t|
      t.text :body
      t.references :commentable, polymorphic: true
      t.timestamps
    end
```

### Single Table Inheritance

```yaml
sti:
  title: "Single Table Inheritance"
  description: "Class hierarchy in one table"
  search_paths:
    - "app/models/**/*.rb"
  code_patterns:
    - "class \\w+ < \\w+"
    - "self\\.inheritance_column"
  keywords: [STI, inheritance, subclass]
  best_practice: |
    # Base class
    class User < ApplicationRecord
      # Common behavior
    end

    # Subclasses
    class Admin < User
      def can_manage_users?
        true
      end
    end

    class Member < User
      def can_manage_users?
        false
      end
    end

    # Migration needs 'type' column
    add_column :users, :type, :string
```

---

## API Patterns

### API Versioning

```yaml
api_versioning:
  title: "API Versioning"
  description: "Version management strategies"
  search_paths:
    - "app/controllers/api/**/*.rb"
    - "app/controllers/api/v*/**/*.rb"
  file_patterns:
    - "api/v*/**/*.rb"
  code_patterns:
    - "module Api::V\\d+"
    - "namespace :api"
  keywords: [api, version, v1, v2]
  best_practice: |
    # config/routes.rb
    namespace :api do
      namespace :v1 do
        resources :users
      end

      namespace :v2 do
        resources :users
      end
    end

    # app/controllers/api/v1/users_controller.rb
    module Api
      module V1
        class UsersController < ApiController
          def index
            render json: User.all
          end
        end
      end
    end
```

### API Serialization

```yaml
api_serialization:
  title: "API Serialization"
  description: "JSON response formatting"
  search_paths:
    - "app/serializers/**/*.rb"
    - "app/blueprints/**/*.rb"
    - "app/views/api/**/*.json.jbuilder"
  file_patterns:
    - "*_serializer.rb"
    - "*_blueprint.rb"
    - "*.json.jbuilder"
  code_patterns:
    - "class \\w+Serializer"
    - "< ActiveModel::Serializer"
    - "< Blueprinter::Base"
    - "json\\."
  keywords: [json, serializer, blueprint, jbuilder]
  best_practice: |
    # Using ActiveModel::Serializers
    class UserSerializer < ActiveModel::Serializer
      attributes :id, :email, :full_name, :created_at

      has_many :posts

      def full_name
        "#{object.first_name} #{object.last_name}"
      end
    end

    # Using Blueprinter
    class UserBlueprint < Blueprinter::Base
      identifier :id

      fields :email, :created_at

      field :full_name do |user|
        "#{user.first_name} #{user.last_name}"
      end

      association :posts, blueprint: PostBlueprint
    end
```

### API Authentication

```yaml
api_authentication:
  title: "API Authentication"
  description: "Token-based authentication"
  search_paths:
    - "app/controllers/api/**/*.rb"
    - "app/controllers/concerns/**/*.rb"
  code_patterns:
    - "before_action :authenticate"
    - "Authorization.*Bearer"
    - "JWT"
    - "authenticate_with_http_token"
  keywords: [auth, token, jwt, bearer]
  best_practice: |
    # app/controllers/api/api_controller.rb
    module Api
      class ApiController < ActionController::API
        before_action :authenticate_user!

        private

        def authenticate_user!
          token = request.headers['Authorization']&.split(' ')&.last
          decoded = JWT.decode(token, Rails.application.secret_key_base, true)
          @current_user = User.find(decoded[0]['user_id'])
        rescue JWT::DecodeError, ActiveRecord::RecordNotFound
          render json: { error: 'Unauthorized' }, status: :unauthorized
        end

        attr_reader :current_user
      end
    end
```

---

## Authorization Patterns

### Policy Objects (Pundit)

```yaml
policies:
  title: "Authorization Policies"
  description: "Pundit policy pattern"
  search_paths:
    - "app/policies/**/*.rb"
  file_patterns:
    - "*_policy.rb"
  code_patterns:
    - "class \\w+Policy"
    - "def initialize\\(user, record\\)"
    - "def index\\?"
    - "def show\\?"
    - "def create\\?"
    - "def update\\?"
    - "def destroy\\?"
  keywords: [pundit, policy, authorization, can]
  best_practice: |
    class PostPolicy
      attr_reader :user, :post

      def initialize(user, post)
        @user = user
        @post = post
      end

      def index?
        true
      end

      def show?
        true
      end

      def create?
        user.present?
      end

      def update?
        user.present? && (post.author == user || user.admin?)
      end

      def destroy?
        user.present? && (post.author == user || user.admin?)
      end

      class Scope
        def initialize(user, scope)
          @user = user
          @scope = scope
        end

        def resolve
          if user&.admin?
            scope.all
          else
            scope.published
          end
        end

        private

        attr_reader :user, :scope
      end
    end
```

---

## Background Job Patterns

### Job Structure

```yaml
background_jobs:
  title: "Background Jobs"
  description: "ActiveJob pattern"
  search_paths:
    - "app/jobs/**/*.rb"
  file_patterns:
    - "*_job.rb"
  code_patterns:
    - "class \\w+Job < ApplicationJob"
    - "def perform"
    - "queue_as"
    - "retry_on"
  keywords: [job, background, async, sidekiq]
  best_practice: |
    class ProcessPaymentJob < ApplicationJob
      queue_as :critical

      retry_on PaymentGateway::NetworkError, wait: 5.seconds, attempts: 3
      discard_on PaymentGateway::InvalidCard

      def perform(payment_id)
        payment = Payment.find(payment_id)
        PaymentProcessor.new(payment).process!
      end
    end

    # Usage:
    ProcessPaymentJob.perform_later(payment.id)
    ProcessPaymentJob.set(wait: 1.hour).perform_later(payment.id)
```

---

## Testing Patterns

### Factory Usage

```yaml
factory_usage:
  title: "FactoryBot Factories"
  description: "Test data creation"
  search_paths:
    - "spec/factories/**/*.rb"
    - "test/factories/**/*.rb"
  file_patterns:
    - "*.rb"
  code_patterns:
    - "FactoryBot\\.define"
    - "factory :\\w+"
    - "trait :\\w+"
  keywords: [factory, factorybot, test data]
  best_practice: |
    FactoryBot.define do
      factory :user do
        sequence(:email) { |n| "user#{n}@example.com" }
        password { "password123" }
        first_name { "John" }
        last_name { "Doe" }

        trait :admin do
          role { :admin }
        end

        trait :with_posts do
          after(:create) do |user|
            create_list(:post, 3, author: user)
          end
        end

        factory :admin_user, traits: [:admin]
      end
    end

    # Usage:
    create(:user)
    create(:user, :admin)
    create(:user, :with_posts)
    build(:user)
```

### Request Specs

```yaml
request_specs:
  title: "Request Specs"
  description: "API endpoint testing"
  search_paths:
    - "spec/requests/**/*_spec.rb"
  code_patterns:
    - "RSpec\\.describe.*type: :request"
    - "get .*"
    - "post .*"
    - "expect\\(response\\)"
  keywords: [request spec, api test, integration test]
  best_practice: |
    RSpec.describe "Api::V1::Users", type: :request do
      let(:user) { create(:user) }
      let(:auth_headers) { { 'Authorization' => "Bearer #{user.token}" } }

      describe "GET /api/v1/users" do
        it "returns users list" do
          create_list(:user, 3)

          get api_v1_users_path, headers: auth_headers

          expect(response).to have_http_status(:ok)
          expect(json_response['users'].size).to eq(4) # 3 + authenticated user
        end
      end

      describe "POST /api/v1/users" do
        let(:valid_params) do
          { user: { email: 'new@example.com', password: 'password123' } }
        end

        it "creates a new user" do
          expect {
            post api_v1_users_path, params: valid_params
          }.to change(User, :count).by(1)

          expect(response).to have_http_status(:created)
        end
      end
    end
```

---

## Decorator Patterns

### Draper Decorators

```yaml
decorators:
  title: "Decorator/Presenter Pattern"
  description: "View logic separation"
  search_paths:
    - "app/decorators/**/*.rb"
    - "app/presenters/**/*.rb"
  file_patterns:
    - "*_decorator.rb"
    - "*_presenter.rb"
  code_patterns:
    - "class \\w+Decorator"
    - "< Draper::Decorator"
    - "delegate_all"
  keywords: [decorator, presenter, view logic]
  best_practice: |
    class UserDecorator < Draper::Decorator
      delegate_all

      def full_name
        "#{first_name} #{last_name}"
      end

      def formatted_created_at
        created_at.strftime("%B %d, %Y")
      end

      def avatar_url
        if object.avatar.attached?
          h.url_for(object.avatar)
        else
          h.asset_path('default-avatar.png')
        end
      end

      def profile_link
        h.link_to full_name, h.user_path(object), class: 'user-link'
      end
    end

    # Usage in controller:
    @user = User.find(params[:id]).decorate

    # Usage in view:
    <%= @user.full_name %>
    <%= @user.profile_link %>
```

---

## Rails 8 Defaults

Rails 8 includes several built-in solutions that replace common third-party gems:

### Solid Queue
**Purpose**: Background job processing (replaces Sidekiq, Resque, Delayed Job)

Rails 8's default background job adapter. Provides:
- Database-backed job queue
- No Redis dependency
- Built-in retry logic
- Job prioritization
- Mission control web UI

**Setup**:
```bash
bin/rails solid_queue:install
```

**Usage**:
```ruby
# config/application.rb or config/environments/production.rb
config.active_job.queue_adapter = :solid_queue

# Jobs work the same as before
class ProcessPaymentJob < ApplicationJob
  queue_as :critical

  def perform(payment_id)
    # Job logic
  end
end
```

### Solid Cache
**Purpose**: Database-backed caching (replaces Redis, Memcached for caching)

Rails 8's default cache store. Provides:
- Database-backed cache
- No Redis dependency
- All standard Rails cache features
- Automatic expiration
- Production-ready performance

**Setup**:
```bash
bin/rails solid_cache:install
```

**Usage**:
```ruby
# config/environments/production.rb
config.cache_store = :solid_cache_store

# Caching works the same as before
Rails.cache.fetch('expensive_query', expires_in: 1.hour) do
  # Expensive operation
end
```

### Solid Cable
**Purpose**: Database-backed Action Cable (replaces Redis for WebSocket pub/sub)

Rails 8's default Action Cable adapter. Provides:
- Database-backed pub/sub
- No Redis dependency for real time features
- WebSocket support
- Horizontal scaling support

**Setup**:
```bash
bin/rails solid_cable:install
```

**Usage**:
```ruby
# config/cable.yml
production:
  adapter: solid_cable

# Channels work the same as before
class ChatChannel < ApplicationCable::Channel
  def subscribed
    stream_from "chat_#{params[:room_id]}"
  end
end
```

### When to Use Rails 8 Defaults

**Use Solid Queue when**:
- Starting new Rails 8 project
- Want to avoid Redis operational complexity
- Job volume < 1000/second
- Prefer simplicity over maximum throughput

**Use Solid Cache when**:
- Starting new Rails 8 project
- Cache hit rates are moderate
- Want unified database infrastructure
- Avoiding Redis operational overhead

**Use Solid Cable when**:
- Starting new Rails 8 project
- Real-time features with moderate concurrency
- Want to simplify infrastructure
- Database can handle WebSocket load

**Consider alternatives when**:
- Extreme performance requirements (millions of jobs/sec)
- Very high cache hit rates (>95%)
- Thousands of concurrent WebSocket connections
- Already have Redis in production

---

## Pattern Categories

The `rails-pattern-finder` skill recognizes these pattern categories:

### Authentication
User login, session management, password handling

**Common implementations**:
- Devise gem
- Rails authentication generator (Rails 8+)
- Custom authentication with `has_secure_password`
- OAuth integrations (OmniAuth)

### Background Jobs
Asynchronous task processing

**Common implementations**:
- Solid Queue (Rails 8 default)
- Sidekiq
- Resque
- Delayed Job
- ActiveJob with any adapter

### Caching
Performance optimization through data caching

**Common implementations**:
- Solid Cache (Rails 8 default)
- Redis cache store
- Memcached
- File store
- Database-backed caching

### Real Time
WebSocket connections and live updates

**Common implementations**:
- Solid Cable (Rails 8 default for Action Cable)
- Action Cable with Redis
- Hotwire Turbo Streams
- Server-Sent Events (SSE)

### File Uploads
Handling user-uploaded files

**Common implementations**:
- Active Storage (Rails built-in)
- Shrine
- CarrierWave
- Paperclip (deprecated)

### Pagination
Dividing large datasets into pages

**Common implementations**:
- Pagy
- Kaminari
- will_paginate
- Custom pagination with `limit/offset`

---

## Usage

Each pattern includes:
- **title**: Human-readable name
- **description**: What the pattern does
- **search_paths**: Where to find files
- **file_patterns**: File naming conventions
- **code_patterns**: Regex to match code structures
- **keywords**: Related concepts
- **best_practice**: Reference implementation

The `rails-pattern-finder` skill uses these definitions to:
1. Search the codebase for existing patterns
2. Extract relevant examples
3. Provide best-practice templates when pattern not found
4. Recommend Rails 8 built-in alternatives when appropriate
