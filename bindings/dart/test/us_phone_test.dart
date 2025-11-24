import 'package:strling/simply.dart';
import 'package:test/test.dart';

void main() {
  group('US Phone Number Pattern', () {
    test('Should build US phone pattern using Simply API', () {
      // Build pattern: ^(\d{3})[-. ]?(\d{3})[-. ]?(\d{4})$
      final pattern = Simply.merge([
        Simply.start(),
        Simply.digit(3, 3).asCapture(),
        Simply.inChars('-. ').optional(),
        Simply.digit(3, 3).asCapture(),
        Simply.inChars('-. ').optional(),
        Simply.digit(4, 4).asCapture(),
        Simply.end(),
      ]);

      // Get the IR
      final ir = pattern.toIR();

      // Verify it's a sequence
      expect(ir['ir'], equals('Seq'));
      expect(ir['parts'], isA<List>());
    });

    test('Should match the TypeScript reference output structure', () {
      // This pattern should produce IR that matches the TypeScript implementation
      final areaCode = Simply.digit(3, 3).asCapture();
      final separator = Simply.inChars('-. ').optional();
      final prefix = Simply.digit(3, 3).asCapture();
      final lineNumber = Simply.digit(4, 4).asCapture();

      final fullPattern = Simply.merge([
        Simply.start(),
        areaCode,
        separator,
        prefix,
        separator,
        lineNumber,
        Simply.end(),
      ]);

      final ir = fullPattern.toIR();

      // The IR should have:
      // - Anchor for Start
      // - Capturing group with \d{3}
      // - Optional character class [-. ]
      // - Capturing group with \d{3}
      // - Optional character class [-. ]
      // - Capturing group with \d{4}
      // - Anchor for End

      expect(ir['ir'], equals('Seq'));
      final parts = ir['parts'] as List;
      
      // Start anchor
      expect(parts[0]['ir'], equals('Anchor'));
      expect(parts[0]['at'], equals('Start'));

      // First capture group - 3 digits
      expect(parts[1]['ir'], equals('Group'));
      expect(parts[1]['capturing'], equals(true));

      // Optional separator
      expect(parts[2]['ir'], equals('Quant'));
      expect(parts[2]['min'], equals(0));
      expect(parts[2]['max'], equals(1));

      // Second capture group - 3 digits
      expect(parts[3]['ir'], equals('Group'));
      expect(parts[3]['capturing'], equals(true));

      // Optional separator
      expect(parts[4]['ir'], equals('Quant'));
      expect(parts[4]['min'], equals(0));
      expect(parts[4]['max'], equals(1));

      // Third capture group - 4 digits
      expect(parts[5]['ir'], equals('Group'));
      expect(parts[5]['capturing'], equals(true));

      // End anchor
      expect(parts[6]['ir'], equals('Anchor'));
      expect(parts[6]['at'], equals('End'));
    });

    test('Should demonstrate various Simply API features', () {
      // Test literal
      final lit = Simply.literal('hello');
      expect(lit.toIR()['ir'], equals('Lit'));
      expect(lit.toIR()['value'], equals('hello'));

      // Test digit with repetition
      final threeDigits = Simply.digit(3, 3);
      final ir = threeDigits.toIR();
      expect(ir['ir'], equals('Quant'));
      expect(ir['min'], equals(3));
      expect(ir['max'], equals(3));

      // Test optional
      final optionalSpace = Simply.literal(' ').optional();
      final optIr = optionalSpace.toIR();
      expect(optIr['ir'], equals('Quant'));
      expect(optIr['min'], equals(0));
      expect(optIr['max'], equals(1));

      // Test capture
      final captured = Simply.digit(3, 3).asCapture();
      final capIr = captured.toIR();
      expect(capIr['ir'], equals('Group'));
      expect(capIr['capturing'], equals(true));

      // Test anyOf
      final choice = Simply.anyOf([Simply.literal('cat'), Simply.literal('dog')]);
      final altIr = choice.toIR();
      expect(altIr['ir'], equals('Alt'));
      expect(altIr['branches'], hasLength(2));

      // Test between
      final lowercaseRange = Simply.between('a', 'z');
      final rangeIr = lowercaseRange.toIR();
      expect(rangeIr['ir'], equals('CharClass'));
      expect(rangeIr['negated'], equals(false));

      // Test anchors
      expect(Simply.start().toIR()['at'], equals('Start'));
      expect(Simply.end().toIR()['at'], equals('End'));
    });

    test('Should handle error cases gracefully', () {
      // Test invalid range
      expect(() => Simply.between(9, 0), throwsA(isA<STRlingError>()));

      // Test mixed case letters
      expect(() => Simply.between('a', 'Z'), throwsA(isA<STRlingError>()));

      // Test empty merge
      expect(() => Simply.merge([]), throwsA(isA<STRlingError>()));

      // Test lazy on non-quantified pattern
      expect(
        () => Simply.literal('x').lazy(),
        throwsA(isA<STRlingError>()),
      );
    });
  });
}
