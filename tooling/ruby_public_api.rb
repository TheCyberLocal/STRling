#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'
require 'pathname'
require 'ripper'

class PublicApiError < StandardError; end

def constant_name(node)
  return nil unless node.is_a?(Array)

  case node[0]
  when :const_ref, :var_ref
    token = node[1]
    token.is_a?(Array) && token[0] == :@const ? token[1] : nil
  when :const_path_ref
    left = constant_name(node[1])
    right = node[2]
    left && right.is_a?(Array) && right[0] == :@const ? "#{left}::#{right[1]}" : nil
  when :top_const_ref
    token = node[1]
    token.is_a?(Array) && token[0] == :@const ? token[1] : nil
  end
end

def identifier(node)
  node.is_a?(Array) && [:@ident, :@label, :@const].include?(node[0]) ? node[1].sub(/:\z/, '') : nil
end

def parameter_name(node)
  return identifier(node) if identifier(node)
  return nil unless node.is_a?(Array)

  identifier(node[1])
end

def parameter_signature(node)
  node = node[1] if node.is_a?(Array) && node[0] == :paren
  return '()' if node.nil?
  raise PublicApiError, 'unsupported Ruby parameter AST' unless node.is_a?(Array) && node[0] == :params

  required, optional, rest, post, keywords, keyword_rest, block = node[1..7]
  values = Array(required).map { |item| parameter_name(item) }
  values.concat(Array(optional).map { |item| "#{parameter_name(item[0])}=?" })
  values << "*#{parameter_name(rest) || ''}" if rest
  values.concat(Array(post).map { |item| parameter_name(item) })
  Array(keywords).each do |item|
    name = parameter_name(item[0])
    values << (item[1] == false ? "#{name}:" : "#{name}:?")
  end
  values << "**#{parameter_name(keyword_rest) || ''}" if keyword_rest
  values << "&#{parameter_name(block) || ''}" if block
  raise PublicApiError, 'unsupported Ruby parameter name' if values.any?(&:nil?)

  "(#{values.join(',')})"
end

def call_name(node)
  return nil unless node.is_a?(Array)

  case node[0]
  when :vcall, :fcall
    identifier(node[1])
  when :command, :command_call
    identifier(node[1])
  when :method_add_arg
    call_name(node[1])
  end
end

def literal_names(node, result = [])
  return result unless node.is_a?(Array)

  if node[0] == :symbol_literal
    name = identifier(node.dig(1, 1)) || identifier(node[1])
    result << name if name
    return result
  end
  node.each { |child| literal_names(child, result) if child.is_a?(Array) }
  result
end

def body_statements(node)
  return [] unless node.is_a?(Array)
  return Array(node[1]) if node[0] == :bodystmt

  Array(node)
end

def walk_body(body, namespace, kind, symbols)
  visibility = :public
  module_function_mode = false
  body_statements(body).each do |statement|
    next unless statement.is_a?(Array)

    case statement[0]
    when :module, :class
      name = constant_name(statement[1])
      raise PublicApiError, "unsupported anonymous Ruby #{statement[0]}" unless name

      qualified = namespace.empty? || name.include?('::') ? name : "#{namespace}::#{name}"
      declaration_kind = statement[0] == :module ? 'module' : 'class'
      symbols["#{declaration_kind}:#{qualified}"] = declaration_kind
      walk_body(statement[2], qualified, declaration_kind.to_sym, symbols)
    when :def
      name = identifier(statement[1])
      signature = parameter_signature(statement[2])
      next unless name && visibility == :public

      prefix = kind == :module && module_function_mode ? 'singleton' : 'instance'
      symbols["#{prefix}:#{namespace}.#{name}"] = signature
    when :defs
      name = identifier(statement[3])
      symbols["singleton:#{namespace}.#{name}"] = parameter_signature(statement[4]) if name
    when :assign
      target = statement[1]
      token = target.dig(1) if target.is_a?(Array) && target[0] == :var_field
      name = identifier(token)
      symbols["constant:#{namespace}::#{name}"] = 'constant' if name
    else
      name = call_name(statement)
      if %w[public protected private].include?(name)
        visibility = name.to_sym
      elsif name == 'module_function'
        names = literal_names(statement)
        if names.empty?
          module_function_mode = true
        else
          names.each do |method_name|
            instance_key = "instance:#{namespace}.#{method_name}"
            signature = symbols.delete(instance_key)
            symbols["singleton:#{namespace}.#{method_name}"] = signature if signature
          end
        end
      elsif %w[attr_reader attr_writer attr_accessor].include?(name) && visibility == :public
        literal_names(statement).each do |attribute|
          symbols["instance:#{namespace}.#{attribute}"] = '()' unless name == 'attr_writer'
          symbols["instance:#{namespace}.#{attribute}="] = '(value)' unless name == 'attr_reader'
        end
      end
    end
  end
end

symbols = {}
ARGV.each do |location|
  matches = Dir.glob(location).select { |path| File.file?(path) && File.extname(path) == '.rb' }.sort
  matches = [location] if matches.empty? && File.file?(location) && File.extname(location) == '.rb'
  matches.each do |path|
    source = File.read(path, encoding: 'UTF-8')
    if Ripper.lex(source).any? { |token| %w[define_method class_eval module_eval].include?(token[2]) }
      raise PublicApiError, "unsupported Ruby public metaprogramming in #{path}"
    end
    sexp = Ripper.sexp(source)
    raise PublicApiError, "cannot parse Ruby public source #{path}" unless sexp

    walk_body([:bodystmt, sexp[1]], '', :root, symbols)
  end
end

raise PublicApiError, 'Ruby public extractor returned no symbols' if symbols.empty?

puts JSON.generate(symbols.sort.to_h)
