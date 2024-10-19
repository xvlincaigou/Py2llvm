grammar Python3Simplified;

// Parser Rules
program: (NEWLINE | statement)* EOF;

statement
    : INDENT* simple_stmt
    | INDENT* compound_stmt
    ;

simple_stmt
    : small_stmt NEWLINE
    ;

small_stmt
    : assignment
    | expr_stmt
    | return_stmt
    ;

compound_stmt
    : if_stmt
    | while_stmt
    | for_stmt
    | funcdef
    ;

assignment: NAME '=' expr;

expr_stmt: expr;

return_stmt: RETURN expr;

test
    : or_test
    ;

or_test
    : and_test (OR and_test)*
    ;

and_test
    : not_test (AND not_test)*
    ;

not_test
    : NOT not_test
    | comparison
    ;

comparison
    : expr (comp_op expr)*
    ;

if_stmt: IF test ':' suite (ELIF test ':' suite)* (ELSE ':' suite)?;

while_stmt: WHILE test ':' suite;

for_stmt: FOR NAME IN expr ':' suite;

funcdef: DEF NAME '(' parameters? ')' ':' suite;

parameters: NAME (',' NAME)*;

suite: simple_stmt | NEWLINE statement+;

comp_op
    : '<' | '>' | '==' | '>=' | '<=' | '!='
    ;

expr
    : expr ('*' | '//' | '/' | '%' | '+' | '-') expr
    | atom
    ;

atom
    : NAME
    | NUMBER
    | STRING
    | 'True' | 'False'
    | '(' expr ')'
    | list
    | func_call
    ;

list: '[' (expr (',' expr)*)? ']';

func_call: NAME '(' (expr (',' expr)*)? ')';

// Lexer Rules

// Define keywords before NAME to avoid conflict
IF: 'if';
ELIF: 'elif';
ELSE: 'else';
WHILE: 'while';
FOR: 'for';
IN: 'in';
DEF: 'def';
RETURN: 'return';
AND: 'and';
OR: 'or';
NOT: 'not';

// NAME should come after the keywords
NAME: [a-zA-Z_][a-zA-Z0-9_]*;
NUMBER: [0-9]+;
STRING: ('"' .*? '"') | ('\'' .*? '\'');

NEWLINE: ('\r'? '\n' | '\r');

INDENT: '\t';
// DEDENT: 'DEDENT';

// SPACES: [\t]+;

// COMMENT: '#' ~[\r\n\f]* -> skip;

// Skip spaces
WS: [ ]+ -> skip;